"""Kedro hooks: pipeline lifecycle wiring for ragcore."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog

from ragcore.adapters.config.settings import (
    InfraSettings,
    get_embedding_runtime_settings,
    get_infra_settings,
)
from ragcore.adapters.runtime import AsyncioRuntime, AsyncioRuntimeFactory
from ragcore.adapters.storage.mongo.run_summary_repository import (
    MongoRunSummaryRepository,
)
from ragcore.adapters.telemetry import (
    JsonlFileTelemetry,
    MongoAuditTelemetryAdapter,
    RunStatsAggregator,
)
from ragcore.adapters.telemetry.factory import assemble_telemetry
from ragcore.adapters.telemetry.registry_aware import RegistryAwareTelemetry
from ragcore.adapters.tracking import build_experiment_tracker
from ragcore.application.publish_collection import CollectionPublisher
from ragcore.application.resolve_relations import ResolveRelationsService
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunSummary
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.experiment_tracker import ExperimentTracker
from ragcore.core.services.run_artifacts import run_scoped_filename
from ragcore.core.services.telemetry_registry import TelemetryRegistry
from ragcore.core.telemetry_events import (
    CHUNK_TRUNCATED,
    EVENT_CATALOG,
    PIPELINE_RUN_COMPLETED,
    PIPELINE_RUN_FAILED,
    PIPELINE_RUN_STARTED,
)
from ragcore.orchestration.kedro.assembly import (
    ReportsTruncations,
    build_processing_stack,
    build_runner,
    prepare_embedder,
)
from ragcore.orchestration.kedro.run_parameters import load_parameters
from ragcore.orchestration.kedro.run_plan import RunPlan, plan_run
from ragcore.orchestration.kedro.stores import (
    MetaStores,
    ensure_indexes,
    open_clients,
    open_document_stores,
    open_meta_stores,
)

logger = logging.getLogger(__name__)


class TelemetryHooks:
    def __init__(self) -> None:
        self._telemetry: RegistryAwareTelemetry | None = None
        self._aggregator: RunStatsAggregator | None = None
        self._context: PipelineContext | None = None
        self._stats_dir: Path | None = None
        self._summary_repo: MongoRunSummaryRepository | None = None
        self._publisher: CollectionPublisher | None = None
        """Publie l'empreinte du run en fin de run, si le bilan dit `ok` (ADR-039)."""
        self._embedder: BaseEmbedder | None = None
        self._runtime_instance: AsyncioRuntime | None = None
        self._tracker: ExperimentTracker | None = None
        """Le tracker d'expériences (§9). Ouvert en tête de run, fermé en fin — dans
        `after_pipeline_run` ET `on_pipeline_error`, pour qu'un run cassé ne laisse pas
        un run MLflow ouvert que le suivant viendrait polluer. `noop` par défaut."""

    @property
    def _runtime(self) -> AsyncioRuntime:
        """Le runtime du HOOK — le sien, pas une boucle globale. Les workers ont le leur.

        **Construit au premier usage, jamais dans `__init__`.** `settings.py` instancie
        `TelemetryHooks()` à l'IMPORT du module, et Kedro `deepcopy` ses settings — donc
        les hooks — quand il ouvre une session (`KedroSession._init_store`). Une boucle
        asyncio n'est pas copiable : allouée dans `__init__`, elle faisait échouer
        `kedro run` avec `TypeError: cannot pickle '_contextvars.Context'` **avant même
        que le pipeline démarre**.

        Un `__init__` pose des attributs ; il n'alloue pas de ressource système. Ici la
        règle n'est pas un principe abstrait — c'est la différence entre un pipeline qui
        se lance et un pipeline qui ne se lance pas.
        """
        if self._runtime_instance is None:
            self._runtime_instance = AsyncioRuntimeFactory().build(worker_id=-1)
        return self._runtime_instance

    @hook_impl
    def before_pipeline_run(
        self, run_params: dict[str, Any], catalog: DataCatalog
    ) -> None:
        """Assemble le run et le POSE au catalogue : le DAG nomme, le hook fournit."""
        settings = get_infra_settings()
        plan = plan_run(load_parameters(catalog), settings, run_params)
        self._start_tracking(settings, plan)
        embedder = prepare_embedder(
            get_embedding_runtime_settings(), plan, self._runtime
        )
        # Gardé pour l'interroger en fin de run : un chunk qu'il a dû raccourcir pour tenir
        # dans la fenêtre du modèle est un chunk dont la fin n'est PAS indexée. Le document
        # est sauvé, le run est complet — mais le bilan doit le dire.
        self._embedder = embedder

        for name, value in self._assemble(settings, plan, embedder).items():
            catalog.save(name, value)

        context, telemetry = self._require_started()
        telemetry.emit(
            build_event(
                event_type=PIPELINE_RUN_STARTED,
                run_id=context.run_id,
                owner_id=context.owner_id,
                source=context.source,
                payload={"pipeline": run_params.get("pipeline_name", "__default__")},
            )
        )

    def _start_tracking(self, settings: InfraSettings, plan: RunPlan) -> None:
        """Ouvre le run d'expérience (§9).

        Le run-id EST le nom de collection — donc le fingerprint du workflow — parce que
        `collection_name` n'est rien d'autre que `fingerprint` : les deux ne peuvent pas
        diverger, ils sortent du même calcul. C'est ce qui lie le run MLflow à sa
        collection Qdrant, et lève l'opacité du hash en portant la `WorkflowConfig` en
        clair. `noop` par défaut : aucun serveur requis, aucune dépendance ajoutée au
        chemin critique.
        """
        self._tracker = build_experiment_tracker(settings)
        self._tracker.start_run(RunId(plan.collection), plan.workflow)

    def _assemble(
        self, settings: InfraSettings, plan: RunPlan, embedder: BaseEmbedder
    ) -> dict[str, object]:
        """Ouvre les dépôts, démarre la télémétrie et rend les entrées du catalogue.

        Les dépôts du HOOK — posés sur SA boucle (self._runtime) — servent les nœuds de
        maintenance (nukeAll, connect, computeIdempotence) et la phase 2, qui ne sont pas
        parallélisés. Les WORKERS de la phase 1 fabriquent LES LEURS (``build_runner``) :
        un dépôt Mongo est lié à la boucle qui l'a touché en premier, donc partager
        ceux-ci avec les workers ferait revenir la globale ``_LOOP`` sous un autre nom
        (§11).
        """
        clients = open_clients(settings)
        ensure_indexes(clients, settings, self._runtime)
        stores = open_document_stores(clients, settings, plan)
        meta = open_meta_stores(clients, settings)
        context, telemetry = self._start_run(settings, plan, meta)
        stack = build_processing_stack(plan, Path(settings.xml_source_path), embedder)
        return {
            "connector": stack.connector,
            "parser": stack.parser,
            "manifest_repo": stores.manifest,
            "doc_repo": stores.documents,
            "graph_repo": stores.graph,
            "vector_repo": stores.vectors,
            # Le pool de la phase 1 : des FABRIQUES, pas des instances (§11).
            "runner": build_runner(settings, plan, context, stack),
            # La phase 2 : un service unique, sur la boucle DU HOOK (pas parallélisé).
            "resolve_service": ResolveRelationsService(
                graph_repo=stores.graph, pending_repo=meta.pending, telemetry=telemetry
            ),
            "pipeline_context": context,
            "telemetry": telemetry,
            # L'agrégat du run, injecté comme les autres objets. C'est le node `report`
            # qui y POUSSE les stats des phases : le hook ne peut pas les tirer du
            # catalogue après coup, Kedro y libère les MemoryDataset dès leur dernier
            # lecteur (cf. `absorb`).
            "run_stats_sink": self,
            # Le runtime du hook, injecté aux nœuds non parallélisés (maintenance +
            # phase 2) comme pont sync→async — l'équivalent déclaré de l'ancienne
            # globale run_async.
            "pipeline_runtime": self._runtime,
        }

    def _start_run(
        self, settings: InfraSettings, plan: RunPlan, meta: MetaStores
    ) -> tuple[PipelineContext, RegistryAwareTelemetry]:
        """Ouvre le contexte du run, sa télémétrie, et le publieur qui tirera la
        conséquence de son bilan."""
        context = PipelineContext.create(
            owner_id=plan.owner_id, source=plan.context_source
        )
        self._context = context
        self._summary_repo = meta.summaries
        self._publisher = CollectionPublisher(
            meta.published, plan.collection, is_full_run=plan.is_full_run
        )
        self._telemetry = self._start_telemetry(
            Path(settings.meta_jsonl_dir), context, meta
        )
        return context, self._telemetry

    def _start_telemetry(
        self, meta_root: Path, context: PipelineContext, meta: MetaStores
    ) -> RegistryAwareTelemetry:
        """Monte la pile de télémétrie du run et l'agrégat qui fera son bilan.

        Le registre est construit depuis le catalogue Python — source de vérité unique.
        """
        self._stats_dir = meta_root / "stats"
        self._stats_dir.mkdir(parents=True, exist_ok=True)
        self._aggregator = RunStatsAggregator(
            run_id=context.run_id,
            owner_id=context.owner_id,
            source=context.source,
            started_at=context.started_at,
        )
        return assemble_telemetry(
            TelemetryRegistry.from_catalog(EVENT_CATALOG),
            jsonl=JsonlFileTelemetry(
                events_dir=meta_root / "events",
                run_id=context.run_id,
                started_at=context.started_at,
            ),
            mongo=MongoAuditTelemetryAdapter(meta.audit, self._runtime),
            aggregate=self._aggregator,
        )

    def _require_started(self) -> tuple[PipelineContext, RegistryAwareTelemetry]:
        """Le contexte et la télémétrie du run, posés par ``_start_run``."""
        if self._context is None or self._telemetry is None:
            msg = "Le run n'est pas démarré : `_start_run` n'a pas été appelé."
            raise RuntimeError(msg)
        return self._context, self._telemetry

    def absorb(self, stats: RunStats) -> None:
        """Reçoit l'agrégat d'une PHASE. **Sans ça, le bilan ment.**

        Chaque worker tient son propre ``RunStats`` (§11) ; ``IngestionRunner`` les réduit
        et les rend dans ``IngestionOutcome.stats``. Mais ce résultat repartait dans un
        ``MemoryDataset`` que **personne ne lisait** : le hook finalisait *son* agrégateur,
        qui n'avait vu que les events du process principal. Le ``document.persisted`` des
        workers — et surtout leurs **compensations** — n'atteignaient jamais le RunSummary,
        donc ``_status_from`` rendait *toujours* ``ok``.

        **Pourquoi le DAG POUSSE au lieu que le hook TIRE.** J'ai d'abord fait lire le
        catalogue au hook en ``after_pipeline_run``. C'était faux, et silencieusement :
        Kedro **libère** un ``MemoryDataset`` dès son dernier consommateur
        (``_release_datasets``). ``ingestion_outcome`` meurt donc avec le node ``report``,
        et le ``load()`` d'après-run échoue. Le catalogue n'est pas un lieu de rendez-vous
        post-run — c'est un tuyau entre nodes, et il se vide derrière eux.
        """
        if self._aggregator is not None:
            self._aggregator.absorb(stats)

    def _declare_truncations(self) -> None:
        """Un chunk raccourci n'est pas une perte, mais ce n'est pas rien : il se DÉCLARE.

        Le document est ingéré (donc l'équation de complétude tombe juste, à raison), mais
        la fin du chunk n'est pas indexée. Un compteur non nul veut dire une seule chose :
        **le `chunk_size` configuré n'est pas compatible avec la fenêtre du modèle**. Le
        run est sauvé ; la configuration, elle, est à corriger.
        """
        if not isinstance(self._embedder, ReportsTruncations):
            return
        truncations = self._embedder.truncations
        if not truncations or self._telemetry is None or self._context is None:
            return
        self._telemetry.emit(
            build_event(
                event_type=CHUNK_TRUNCATED,
                run_id=self._context.run_id,
                owner_id=self._context.owner_id,
                source=self._context.source,
                payload={"count": truncations},
            )
        )
        logger.warning(
            "%d chunk(s) raccourci(s) pour tenir dans la fenêtre du modèle. Le corpus est "
            "complet, mais la fin de ces chunks n'est pas indexée : baisser `chunk_size`.",
            truncations,
        )

    def _drain_and_declare(self) -> None:
        """Attend les écritures d'audit en vol, et DÉCLARE celles qui ont échoué.

        À appeler avant ``_persist_run_summary`` : le compte doit entrer dans l'agrégat
        pour que ``_status_from`` le voie. Après, le bilan est déjà écrit.

        Le drain n'est pas la fermeture — ``_persist_run_summary`` a encore besoin de la
        boucle (il y écrit le sommaire, de façon *synchrone* : il n'y laisse donc rien en
        vol). C'est bien pour ça que le port sépare ``drain()`` de ``close()``.
        """
        report = self._runtime.drain()
        if not report.failed:
            return
        if self._aggregator is not None:
            self._aggregator.record_audit_failure("drain", report.failed)
        logger.error(
            "%d écriture(s) d'audit PERDUE(S) : le bilan de ce run repose sur des "
            "compteurs incomplets — il est déclaré `degraded`.",
            report.failed,
        )

    def _persist_run_summary(
        self, status: str, error_message: str | None = None
    ) -> RunSummary | None:
        """Finalise l'agrégateur et persiste le RunSummary (fichier JSON + Mongo).

        Rend le bilan : le statut annoncé n'est **pas** celui qui sort (``finalize``
        le re-dérive des compteurs). L'appelant qui veut savoir si le run est vraiment
        `ok` — pour publier, par exemple — doit lire le bilan, pas ce qu'il a demandé.
        """
        if (
            self._aggregator is None
            or self._stats_dir is None
            or self._summary_repo is None
        ):
            return None
        summary = self._aggregator.finalize(status=status, error_message=error_message)  # type: ignore[arg-type]
        path = self._stats_dir / run_scoped_filename(
            summary.run_id, summary.started_at, ".json"
        )
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._runtime.run(self._summary_repo.upsert(summary))
        return summary

    def _publish(self, summary: RunSummary | None) -> None:
        """Publie l'empreinte du run si le bilan le permet (``CollectionPublisher``).

        Sans bilan ou sans publieur (hook jamais câblé), il n'y a rien à publier.
        """
        if summary is None or self._publisher is None:
            return
        self._runtime.run(self._publisher.publish_if_complete(summary))

    def _track_and_close(self, summary: RunSummary | None) -> None:
        """Enregistre le bilan dans le tracker, puis ferme le run — **toujours**.

        Appelé depuis `after_pipeline_run` ET `on_pipeline_error` : quel que soit le
        sort du pipeline, le run d'expérience doit être clos, sinon le suivant se
        grefferait sur un run resté ouvert. `end_run` est en `finally` pour cette
        raison — une exception dans `log_summary` (backend injoignable) ne doit pas
        laisser le run pendant.

        Un `summary` à `None` (agrégateur/dépôts non initialisés) n'a rien à logguer,
        mais le run peut malgré tout avoir été ouvert : on ferme quand même.
        """
        if self._tracker is None:
            return
        try:
            if summary is not None:
                self._tracker.log_summary(summary)
        finally:
            self._tracker.end_run()

    @hook_impl
    def after_pipeline_run(self, run_params: dict[str, Any]) -> None:
        if self._telemetry and self._context:
            self._telemetry.emit(
                build_event(
                    event_type=PIPELINE_RUN_COMPLETED,
                    run_id=self._context.run_id,
                    owner_id=self._context.owner_id,
                    source=self._context.source,
                    payload={
                        "pipeline": run_params.get("pipeline_name", "__default__")
                    },
                )
            )
        # Les chunks que l'embedder a dû raccourcir. Le compteur vit sur l'embedder (il
        # est le seul à voir le refus du service) et il est lu ICI, une fois, en fin de
        # run. Les WRITES pendant le run viennent de plusieurs workers : l'embedder les
        # protège lui-même (verrou + ensemble de chunk_ids). La lecture, elle, est
        # postérieure à tous les workers — et le port `BaseEmbedder` n'a pas à connaître
        # la télémétrie pour un détail qui ne concerne qu'une de ses implémentations.
        self._declare_truncations()

        # Le drain AVANT le bilan, et l'ordre est tout l'enjeu : c'est lui qui révèle
        # les écritures d'audit perdues, et un bilan persisté avant de le savoir ne peut
        # pas en tenir compte. Il déclarerait `ok` un run dont il ne peut plus prouver la
        # complétude — exactement le mensonge qu'on cherche à rendre impossible.
        self._drain_and_declare()

        # Les stats des workers ont déjà été POUSSÉES ici par le node `report` (cf.
        # `absorb`). `_persist_run_summary` dérive le statut de ces compteurs : sans eux,
        # pas un seul document perdu ne serait visible, et le run serait `ok` quoi qu'il
        # arrive.
        summary = self._persist_run_summary(status="ok")

        # Et SEULEMENT si ce bilan dit `ok`, on publie l'empreinte : c'est ce que le
        # serving lira. Un run dégradé ne publie pas — le dernier corpus complet reste
        # en place. La publication est la CONSÉQUENCE du bilan, jamais son présupposé.
        self._publish(summary)

        # Le bilan part aussi vers le tracker (§9), et le run d'expérience se ferme. En
        # `noop` c'est sans effet ; en MLflow, c'est ici que le fingerprint devient un
        # run consultable, paramètres et compteurs en clair.
        self._track_and_close(summary)

        self._runtime.close()

    @hook_impl
    def on_pipeline_error(self, error: Exception, run_params: dict[str, Any]) -> None:
        if self._telemetry and self._context:
            self._telemetry.emit(
                build_event(
                    event_type=PIPELINE_RUN_FAILED,
                    run_id=self._context.run_id,
                    owner_id=self._context.owner_id,
                    source=self._context.source,
                    payload={
                        "pipeline": run_params.get("pipeline_name", "__default__"),
                        "error": str(error),
                    },
                    success=False,
                    error_message=str(error),
                )
            )
        # Les chunks raccourcis se déclarent AUSSI sur un run cassé. Le raccourcissement a
        # bien eu lieu (l'embedder a tourné avant l'échec) et il pointe une config à
        # corriger : le taire parce que le run a cassé plus loin perdrait l'indice. Émis
        # AVANT le drain, comme dans le chemin nominal, pour que l'événement soit vidé.
        self._declare_truncations()

        # Drainer AVANT le bilan, ici aussi : le statut restera `failed` de toute façon
        # (il ne se dérive pas des compteurs), mais le compteur `audit.write.failed`
        # doit figurer dans le bilan — sur un run qui a cassé, savoir si la trace elle
        # aussi est trouée décide de ce qu'on peut conclure du reste.
        self._drain_and_declare()

        # ⚠️ Le bilan sera PAUVRE : les stats des workers ne remontent que par le node
        # `report`, qui est terminal. Un pipeline qui casse avant lui ne persiste que les
        # compteurs du process principal. Le statut `failed` reste vrai — c'est son
        # détail qui manque.
        summary = self._persist_run_summary(status="failed", error_message=str(error))

        # Même sur un run cassé, le run d'expérience doit être clos — un run MLflow
        # laissé ouvert verrait le prochain lancement s'y greffer. Le bilan est pauvre
        # (cf. plus haut), mais son statut `failed` est vrai et mérite d'être tracé.
        self._track_and_close(summary)

        self._runtime.close()
