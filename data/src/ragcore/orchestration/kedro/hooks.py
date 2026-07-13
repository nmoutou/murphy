"""Kedro hooks: pipeline lifecycle wiring for ragcore."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog

from ragcore.adapters.config.settings import (
    get_embedding_runtime_settings,
    get_infra_settings,
)
from ragcore.adapters.embedding.local_embedder import LocalEmbedder
from ragcore.adapters.embedding.noop_embedder import NoopEmbedder
from ragcore.adapters.embedding.openai_embedder import (
    OpenAIEmbedder,
    assert_service_serves_model,
)
from ragcore.adapters.runtime import AsyncioRuntime, AsyncioRuntimeFactory
from ragcore.adapters.storage.mongo.audit_repository import MongoAuditRepository
from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.manifest_repository import MongoManifestRepository
from ragcore.adapters.storage.mongo.pending_repository import (
    MongoPendingRelationRepository,
)
from ragcore.adapters.storage.mongo.run_summary_repository import (
    MongoRunSummaryRepository,
)
from ragcore.adapters.storage.mongo.schemas import (
    ensure_data_indexes,
    ensure_meta_indexes,
)
from ragcore.adapters.storage.neo4j.client import create_neo4j_driver
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.qdrant.client import create_qdrant_client
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.adapters.telemetry import (
    JsonlFileTelemetry,
    MongoAuditTelemetryAdapter,
    RunStatsAggregator,
)
from ragcore.adapters.telemetry.console_log import ConsoleLogTelemetry
from ragcore.adapters.telemetry.factory import WorkerTelemetryFactory
from ragcore.adapters.telemetry.registry_aware import RegistryAwareTelemetry
from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.ingestion_runner import IngestionRunner
from ragcore.application.resolve_relations import ResolveRelationsService
from ragcore.application.run_context import PipelineContext
from ragcore.core.config import (
    ChunkingConfig,
    EmbeddingConfig,
    NormalizationConfig,
    WorkflowConfig,
    collection_name,
)
from ragcore.core.models.audit import build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.services.telemetry_registry import TelemetryRegistry
from ragcore.core.telemetry_events import (
    EVENT_CATALOG,
    PIPELINE_RUN_COMPLETED,
    PIPELINE_RUN_FAILED,
    PIPELINE_RUN_STARTED,
)
from ragcore.orchestration.kedro.workload import build_document_workload
from ragcore.sources.generic import (
    GenericParser,
    GenericRelationExtractor,
    StructuralChunker,
)
from ragcore.sources.registry import definition_for

logger = logging.getLogger(__name__)

# Le pool de la phase 1. Un jour un paramètre ; pour l'instant une constante nommée,
# et non un « 4 » nu perdu dans le constructeur du runner.
_WORKER_COUNT = 4


def _stats_filename(run_id: str, started_at: datetime) -> str:
    iso = started_at.strftime("%Y-%m-%dT%H.%M.%S.") + f"{started_at.microsecond // 1000:03d}Z"
    return f"{iso}_{run_id}.json"


class TelemetryHooks:
    def __init__(self) -> None:
        self._telemetry: RegistryAwareTelemetry | None = None
        self._aggregator: RunStatsAggregator | None = None
        self._context: PipelineContext | None = None
        self._stats_dir: Path | None = None
        self._summary_repo: MongoRunSummaryRepository | None = None
        self._runtime_instance: AsyncioRuntime | None = None

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
    def before_pipeline_run(  # noqa: PLR0915 — pur câblage : construire les clients puis POSER chaque objet au catalogue est un inventaire, pas de la logique ; le fractionner disperserait l'assemblage
        self, run_params: dict, catalog: DataCatalog
    ) -> None:
        settings = get_infra_settings()
        embedding_settings = get_embedding_runtime_settings()

        # Charger les paramètres Kedro (parameters.yml)
        try:
            params = catalog.load("parameters")
        except Exception:
            # Si les paramètres ne sont pas disponibles, utiliser des valeurs par défaut
            params = {}

        # La config de workflow — LA référence (§9). `parameters.yml` n'est qu'une façon
        # de la peupler : c'est ici que Kedro cesse d'être la vérité et redevient un
        # shell. Un CLI ou un test construit le même objet sans qu'aucun YAML n'existe.
        workflow = _build_workflow_config(params)

        # La collection Qdrant est DÉRIVÉE, plus configurée (§6). Elle porte l'empreinte
        # de ce qui produit les vecteurs : changer le chunk_size crée mécaniquement une
        # collection neuve, et les deux coexistent — c'est ce qui rend l'A/B possible.
        # Un `collection:` écrit à la main dans le YAML permettait au contraire d'écraser
        # les vecteurs d'une stratégie avec ceux d'une autre, sans que rien ne le signale.
        qdrant_collection = collection_name(workflow)
        logger.info(
            "Collection Qdrant dérivée de la config de workflow : %s", qdrant_collection
        )

        # Le modèle qui vient de BAPTISER la collection est-il celui que le service SERT ?
        #
        # TEI ne sert qu'un modèle — celui de son `--model-id` — et ignore le champ `model`
        # de la requête. Si le conteneur et `parameters.yml` divergent, on écrit les
        # vecteurs d'un modèle dans la collection nommée d'après un autre : rien ne lève,
        # rien ne loggue, et ça ne se voit qu'à la recherche.
        #
        # C'est une PRÉCONDITION du run, et c'est pourquoi elle est ici et pas dans
        # l'embedder : `SagaExecutor` attrape `Exception` pour compenser, donc levée dans
        # un worker elle deviendrait un échec par document — compensé N fois, avec un run
        # qui conclut « ok ». Vérifier N fois quel modèle le service sert n'aurait de toute
        # façon aucun sens : il n'en sert qu'un, et il le dit une fois pour toutes.
        if embedding_settings.provider == "openai":
            self._runtime.run(
                assert_service_serves_model(
                    embedding_settings.service_url or "",
                    workflow.embedding.model_name,
                )
            )
        elif embedding_settings.provider == "noop":
            # `provider` n'entre PAS dans l'empreinte (§6) : deux façons d'atteindre le
            # même modèle produisent les mêmes vecteurs. Mais `noop` n'atteint aucun
            # modèle — il produit des vecteurs NULS, et les écrit dans la collection du
            # vrai modèle, où plus rien ne les distingue ensuite. La doctrine assume la
            # verrue ; elle n'exige pas qu'elle soit muette.
            logger.warning(
                "EMBEDDING_PROVIDER=noop : les vecteurs seront NULS et seront écrits dans "
                "la collection %s — celle du vrai modèle, où rien ne les distinguera. "
                "Hygiène de test uniquement : pour un vrai run, EMBEDDING_PROVIDER=openai.",
                qdrant_collection,
            )

        # Infrastructure clients
        mongo_client = create_mongo_client(settings.mongodb_uri)
        neo4j_driver = create_neo4j_driver(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password.get_secret_value(),
        )
        qdrant_client = create_qdrant_client(
            settings.qdrant_url,
            settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
        )

        # Créer les indexes MongoDB
        data_db = settings.mongodb_data_db_name
        meta_db = settings.mongodb_meta_db_name
        self._runtime.run(ensure_data_indexes(mongo_client[data_db]))
        self._runtime.run(ensure_meta_indexes(mongo_client[meta_db]))

        # Repositories du HOOK — posés sur SA boucle (self._runtime). Ils servent les
        # nœuds de maintenance (forceDrop, connect, computeIdempotence) et la phase 2,
        # qui ne sont pas parallélisés. Les WORKERS de la phase 1 fabriquent LES LEURS
        # (cf. use_case_factory plus bas) : un dépôt Mongo est lié à la boucle qui l'a
        # touché en premier, donc partager ceux-ci avec les workers ferait revenir la
        # globale ``_LOOP`` sous un autre nom (§11).
        doc_repo = MongoDocumentRepository(mongo_client, data_db)
        manifest_repo = MongoManifestRepository(mongo_client, data_db)
        audit_repo = MongoAuditRepository(mongo_client, meta_db)
        summary_repo = MongoRunSummaryRepository(mongo_client, meta_db)
        pending_repo = MongoPendingRelationRepository(mongo_client, meta_db)
        graph_repo = Neo4jGraphRepository(neo4j_driver)
        vector_repo = QdrantVectorRepository(
            qdrant_client, qdrant_collection, workflow.embedding.dimension
        )

        # Pipeline context (created early so telemetry adapters can use the run_id)
        extra = run_params.get("extra_params") or {}
        owner_id = extra.get("owner_id", settings.owner_id)

        # La SOURCE du run — plus câblée en dur sur LEGI. Six sources sont ingérables
        # (`sources/registry.py`), et on en choisit une :
        #
        #     kedro run --params source=cass
        #
        # Une seule source par run, délibérément : le manifest, les agrégats et le
        # RunSummary sont tous indexés par source, et un run qui en mélangerait deux
        # rendrait son propre bilan illisible. Ingérer les cinq juri, c'est cinq runs —
        # ce qui est aussi ce que permet de les rejouer indépendamment.
        source = _resolve_source(extra.get("source", settings.source))
        definition = definition_for(source)

        self._context = PipelineContext.create(
            owner_id=OwnerId(owner_id),
            source=source,
        )
        logger.info("Source du run : %s", source.value)

        # Telemetry stack — configurable par registry
        meta_root = Path(settings.meta_jsonl_dir)

        # Registry construit depuis le catalogue Python — source de vérité unique
        registry = TelemetryRegistry.from_catalog(EVENT_CATALOG)

        jsonl_telemetry = JsonlFileTelemetry(
            events_dir=meta_root / "events",
            run_id=self._context.run_id,
            started_at=self._context.started_at,
        )
        self._stats_dir = meta_root / "stats"
        self._stats_dir.mkdir(parents=True, exist_ok=True)
        self._summary_repo = summary_repo
        self._aggregator = RunStatsAggregator(
            run_id=self._context.run_id,
            owner_id=self._context.owner_id,
            source=self._context.source,
            started_at=self._context.started_at,
        )
        self._telemetry = RegistryAwareTelemetry(
            registry=registry,
            backends={
                "log": ConsoleLogTelemetry(),
                "jsonl": jsonl_telemetry,
                "mongo": MongoAuditTelemetryAdapter(audit_repo, self._runtime),
                "aggregate": self._aggregator,
            },
        )

        # **Aucun nom de source ici.** Le parser, le chunker et l'extracteur sont
        # génériques (§3) ; le connecteur vient du registre. Ce bloc est identique pour
        # LEGI et pour les cinq juri — c'est très exactement la mesure du succès :
        # ajouter une source n'a demandé aucune ligne dans le hook.
        #
        # Purs (chunker, parser, extracteur) ou créant leur client à l'appel (embedder) :
        # partageables entre workers sans risque.
        connector = definition.connector(
            Path(settings.xml_source_path) / definition.subdirectory
        )
        parser = GenericParser(definition.table, source)
        chunker = StructuralChunker(
            max_chunk_size=workflow.chunking.size, overlap=workflow.chunking.overlap
        )
        relation_extractor = GenericRelationExtractor(definition.table, source)

        # Embedding : le MODÈLE et la DIMENSION viennent du workflow (ils décident des
        # vecteurs, donc ils sont hashés) ; le PROVIDER et son transport viennent de
        # l'infra (ils ne changent aucun vecteur). La couture passe exactement ici.
        embedding = workflow.embedding
        if embedding_settings.provider == "local":
            embedder: object = LocalEmbedder(
                model_name=embedding.model_name,
                dimension=embedding.dimension,
            )
        elif embedding_settings.provider == "noop":
            embedder = NoopEmbedder(dimension=embedding.dimension)
        else:
            embedder = OpenAIEmbedder(
                api_key=embedding_settings.api_key,
                model_name=embedding.model_name,
                dimension=embedding.dimension,
                batch_size=embedding_settings.batch_size,
                base_url=embedding_settings.service_url,
            )

        # --- Le pool de la phase 1 : des FABRIQUES, pas des instances (§11) ---------
        runner = self._build_runner(
            chunker, embedder, relation_extractor, qdrant_collection, workflow
        )

        # --- La phase 2 : un service unique, sur la boucle DU HOOK (pas parallélisé) -
        resolve_service = ResolveRelationsService(
            graph_repo=graph_repo,
            pending_repo=pending_repo,
            telemetry=self._telemetry,
        )

        # Populate catalog for node injection
        catalog.save("connector", connector)
        catalog.save("parser", parser)
        catalog.save("manifest_repo", manifest_repo)
        catalog.save("doc_repo", doc_repo)
        catalog.save("graph_repo", graph_repo)
        catalog.save("vector_repo", vector_repo)
        catalog.save("runner", runner)
        catalog.save("resolve_service", resolve_service)
        catalog.save("pipeline_context", self._context)
        catalog.save("telemetry", self._telemetry)
        # Le runtime du hook, injecté aux nœuds non parallélisés (maintenance + phase 2)
        # comme pont sync→async — l'équivalent déclaré de l'ancienne globale run_async.
        catalog.save("pipeline_runtime", self._runtime)

        self._telemetry.emit(
            build_event(
                event_type=PIPELINE_RUN_STARTED,
                run_id=self._context.run_id,
                owner_id=self._context.owner_id,
                source=self._context.source,
                payload={"pipeline": run_params.get("pipeline_name", "__default__")},
            )
        )

    def _build_runner(  # noqa: PLR0913 — chaque argument est une pièce du pool ; les grouper cacherait ce qu'on assemble
        self,
        chunker: StructuralChunker,
        embedder: object,
        extractor: GenericRelationExtractor,
        qdrant_collection: str,
        workflow: WorkflowConfig,
    ) -> IngestionRunner:
        """Assemble le pool de la phase 1 : deux fabriques + un use case PAR worker.

        Extrait de ``before_pipeline_run`` pour tenir en un bloc cohérent — c'est ici
        que se joue tout le §11. ``self._context`` est déjà posé quand cette méthode
        est appelée. ``qdrant_collection`` est **dérivé du ``workflow``** (§6) et DOIT
        être celui du ``vector_repo`` du hook — d'où le passage explicite plutôt qu'un
        second appel à ``collection_name`` : deux dérivations, c'est deux occasions de
        diverger, et workers et phase 2 écriraient alors dans deux collections.
        """
        settings = get_infra_settings()
        data_db = settings.mongodb_data_db_name
        meta_db = settings.mongodb_meta_db_name
        events_dir = Path(settings.meta_jsonl_dir) / "events"
        context = self._context
        assert context is not None  # posé en tête de before_pipeline_run

        runtime_factory = AsyncioRuntimeFactory()
        telemetry_factory = WorkerTelemetryFactory(
            run_id=context.run_id,
            owner_id=context.owner_id,
            source=context.source,
            started_at=context.started_at,
            events_dir=events_dir,
            audit_repo_factory=lambda runtime: MongoAuditRepository(
                create_mongo_client(settings.mongodb_uri), meta_db
            ),
        )

        def use_case_factory(telemetry: WorkerTelemetry) -> IngestDocumentUseCase:
            """Un use case PAR worker, sur des dépôts NEUFS et sa propre télémétrie.

            Les clients sont recréés ici : un client Motor/Neo4j/Qdrant est lié à la
            boucle du worker qui l'appelle en premier. Réutiliser ceux du hook les
            lierait à la boucle du hook, et tous les workers échoueraient sauf un.
            """
            worker_mongo = create_mongo_client(settings.mongodb_uri)
            worker_neo4j = create_neo4j_driver(
                settings.neo4j_uri,
                settings.neo4j_username,
                settings.neo4j_password.get_secret_value(),
            )
            worker_qdrant = create_qdrant_client(
                settings.qdrant_url,
                settings.qdrant_api_key.get_secret_value()
                if settings.qdrant_api_key
                else None,
            )
            return IngestDocumentUseCase(
                document_repo=MongoDocumentRepository(worker_mongo, data_db),
                graph_repo=Neo4jGraphRepository(worker_neo4j),
                vector_repo=QdrantVectorRepository(
                    worker_qdrant, qdrant_collection, workflow.embedding.dimension
                ),
                manifest_repo=MongoManifestRepository(worker_mongo, data_db),
                telemetry=telemetry,
            )

        workload = build_document_workload(
            chunker=chunker,
            embedder=embedder,  # type: ignore[arg-type]
            extractor=extractor,
            use_case_factory=use_case_factory,
            context=context,
        )
        return IngestionRunner(
            workload=workload,
            runtime_factory=runtime_factory,
            telemetry_factory=telemetry_factory,
            worker_count=_WORKER_COUNT,
        )

    def _persist_run_summary(
        self, status: str, error_message: str | None = None
    ) -> None:
        """Finalise l'agrégateur et persiste le RunSummary (fichier JSON + Mongo)."""
        if self._aggregator is None or self._stats_dir is None or self._summary_repo is None:
            return
        summary = self._aggregator.finalize(status=status, error_message=error_message)  # type: ignore[arg-type]
        path = self._stats_dir / _stats_filename(summary.run_id, summary.started_at)
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._runtime.run(self._summary_repo.upsert(summary))

    @hook_impl
    def after_pipeline_run(self, run_params: dict) -> None:
        if self._telemetry and self._context:
            self._telemetry.emit(
                build_event(
                    event_type=PIPELINE_RUN_COMPLETED,
                    run_id=self._context.run_id,
                    owner_id=self._context.owner_id,
                    source=self._context.source,
                    payload={"pipeline": run_params.get("pipeline_name", "__default__")},
                )
            )
        self._persist_run_summary(status="ok")
        # Draine les écritures d'audit en vol, puis ferme. C'est ici que se joue
        # l'at-least-once : fermer sans drainer, c'est perdre la trace du run.
        self._runtime.close()

    @hook_impl
    def on_pipeline_error(self, error: Exception, run_params: dict) -> None:
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
        self._persist_run_summary(status="failed", error_message=str(error))
        # Draine les écritures d'audit en vol, puis ferme. C'est ici que se joue
        # l'at-least-once : fermer sans drainer, c'est perdre la trace du run.
        self._runtime.close()


def _build_workflow_config(params: dict[str, Any]) -> WorkflowConfig:
    """``parameters.yml`` → ``WorkflowConfig``. La seule traduction, et elle est ici.

    C'est le point où Kedro cesse d'être la vérité (§9) : le YAML *peuple* la config,
    il ne la *définit* pas. Cette fonction est le seul endroit du dépôt qui connaisse la
    forme du YAML ; ``core/`` n'en sait rien et ne doit rien en savoir.

    Les défauts ne sont pas des valeurs de confort : chacun est une décision qui sera
    hashée. Un défaut qui change en silence change le nom de la collection, donc écrit
    les vecteurs ailleurs — d'où le cliquet ``golden/test_fingerprint.py``.
    """
    formatting = params.get("formatting", {})
    chunking = formatting.get("chunking", {})
    normalization = formatting.get("normalization", {})
    embedding = params.get("embedding", {}).get("embedding", {})

    return WorkflowConfig(
        normalization=NormalizationConfig(
            # §4 n'est pas écrite : il n'y a aujourd'hui AUCUNE normalisation
            # typographique. « none » le dit. Le jour où elle atterrit, elle exporte sa
            # version, ce champ la lit, et la collection change toute seule.
            version=normalization.get("version", "none"),
        ),
        chunking=ChunkingConfig(
            strategy=chunking.get("strategy", "legi-structural-v1"),
            size=chunking.get("chunk_size", 128),
            overlap=chunking.get("chunk_overlap", 25),
        ),
        embedding=EmbeddingConfig(
            model_name=embedding.get(
                "embedding_model", "sentence-transformers/all-mpnet-base-v2"
            ),
            dimension=embedding.get("dimension", 768),
        ),
    )


def _resolve_source(value: str | SourceName) -> SourceName:
    """La source demandée, ou une erreur qui dit quoi faire.

    Un ``--params source=cas`` (faute de frappe) doit échouer **au démarrage**, en nommant
    les sources valides. Sans ça, Kedro partirait sur une source inconnue et le run
    n'ingérerait rien — un échec silencieux qui ressemble à un corpus vide.
    """
    if isinstance(value, SourceName):
        return value
    try:
        return SourceName(str(value).lower())
    except ValueError as exc:
        connues = ", ".join(sorted(s.value for s in SourceName))
        msg = f"Source inconnue : {value!r}. Sources déclarées : {connues}."
        raise ValueError(msg) from exc
