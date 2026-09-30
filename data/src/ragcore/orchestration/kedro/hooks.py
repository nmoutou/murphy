"""Kedro hooks : le cycle de vie du run, câblé sur l'assemblage de ragcore.

Le hook vit le temps du process ; il ouvre une ``RunSession`` en tête de run et la clôt
en fin. L'assemblage vit dans ``run_plan``, ``stores`` et ``assembly`` ; l'état du run et
sa clôture dans ``run_session``.
"""

from __future__ import annotations

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
from ragcore.application.resolve_relations import ResolveRelationsService
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.enums import SourceName
from ragcore.core.models.run_summary import RunStatus
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.telemetry_events import (
    PIPELINE_RUN_COMPLETED,
    PIPELINE_RUN_FAILED,
    PIPELINE_RUN_STARTED,
)
from ragcore.orchestration.kedro.assembly import (
    build_processing_stack,
    build_runner,
    prepare_embedder,
)
from ragcore.orchestration.kedro.run_parameters import load_parameters
from ragcore.orchestration.kedro.run_plan import RunPlan, plan_run
from ragcore.orchestration.kedro.run_session import RunSession, start_telemetry
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
        self._runtime_instance: AsyncioRuntime | None = None
        self._session: RunSession | None = None
        """La session du run en cours : posée par ``before_pipeline_run``, absente tant
        que l'assemblage n'a pas abouti."""

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
        embedder = prepare_embedder(
            get_embedding_runtime_settings(), plan, self._runtime
        )
        for name, value in self._assemble(settings, plan, embedder).items():
            catalog.save(name, value)
        if self._session is not None:
            self._session.emit_lifecycle_event(PIPELINE_RUN_STARTED, run_params)

    def _assemble(
        self, settings: InfraSettings, plan: RunPlan, embedder: BaseEmbedder
    ) -> dict[str, object]:
        """Ouvre les dépôts et la session du run, et rend les entrées du catalogue.

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
        session = self._open_session(settings, plan.context_source, meta, embedder)
        stack = build_processing_stack(plan, Path(settings.xml_source_path), embedder)
        return {
            "connector": stack.connector,
            "parser": stack.parser,
            "manifest_repo": stores.manifest,
            "doc_repo": stores.documents,
            "graph_repo": stores.graph,
            "vector_repo": stores.vectors,
            # Le pool de la phase 1 : des FABRIQUES, pas des instances (§11).
            "runner": build_runner(settings, plan, session.context, stack),
            # La phase 2 : un service unique, sur la boucle DU HOOK (pas parallélisé).
            "resolve_service": ResolveRelationsService(
                graph_repo=stores.graph,
                pending_repo=meta.pending,
                telemetry=session.telemetry,
            ),
            "pipeline_context": session.context,
            "telemetry": session.telemetry,
            # L'agrégat du run lui-même, que le node `report` alimente des stats des
            # workers (cf. `RunStatsSink`). Sans cette poussée, le bilan ne verrait que
            # le process principal — jamais une compensation — et le run serait `ok`
            # quoi qu'il arrive. Le hook ne peut pas tirer ces stats du catalogue après
            # coup : Kedro libère un MemoryDataset dès son dernier lecteur.
            "run_stats_sink": session.aggregator,
            # Le runtime du hook, injecté aux nœuds non parallélisés (maintenance +
            # phase 2) comme pont sync→async — l'équivalent déclaré de l'ancienne
            # globale run_async.
            "pipeline_runtime": self._runtime,
            # Des réglages du plan, pas des objets vivants : déjà validés par `plan_run`.
            "skip_unconfigured": plan.skip_unconfigured,
            "nuke_all": plan.nuke_all,
        }

    def _open_session(
        self,
        settings: InfraSettings,
        source: SourceName | None,
        meta: MetaStores,
        embedder: BaseEmbedder,
    ) -> RunSession:
        """Ouvre le contexte du run et sa télémétrie."""
        meta_root = Path(settings.meta_jsonl_dir)
        stats_dir = meta_root / "stats"
        stats_dir.mkdir(parents=True, exist_ok=True)
        context = PipelineContext.create(source=source)
        telemetry, aggregator = start_telemetry(
            meta_root, context, meta.audit, self._runtime
        )
        self._session = RunSession(
            context=context,
            telemetry=telemetry,
            aggregator=aggregator,
            stats_dir=stats_dir,
            summaries=meta.summaries,
            embedder=embedder,
            runtime=self._runtime,
        )
        return self._session

    @hook_impl
    def after_pipeline_run(self, run_params: dict[str, Any]) -> None:
        if self._session is not None:
            self._session.emit_lifecycle_event(PIPELINE_RUN_COMPLETED, run_params)
            self._session.close(RunStatus.OK)
        self._close_runtime()

    @hook_impl
    def on_pipeline_error(self, error: Exception, run_params: dict[str, Any]) -> None:
        if self._session is not None:
            self._session.emit_lifecycle_event(PIPELINE_RUN_FAILED, run_params, error)
            # ⚠️ Le bilan sera PAUVRE : les stats des workers ne remontent que par le
            # node `report`, qui est terminal. Un pipeline qui casse avant lui ne
            # persiste que les compteurs du process principal. Le statut `failed` reste
            # vrai — c'est son détail qui manque.
            self._session.close(RunStatus.FAILED, error_message=str(error))
        self._close_runtime()

    def _close_runtime(self) -> None:
        """Ferme la boucle du hook — si elle a jamais été ouverte."""
        if self._runtime_instance is not None:
            self._runtime_instance.close()
