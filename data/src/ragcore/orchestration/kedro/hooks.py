"""Kedro hooks: pipeline lifecycle wiring for ragcore."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog

from ragcore.adapters.embedding.local_embedder import LocalEmbedder
from ragcore.adapters.embedding.noop_embedder import NoopEmbedder
from ragcore.adapters.embedding.openai_embedder import OpenAIEmbedder
from ragcore.adapters.storage.mongo.audit_repository import MongoAuditRepository
from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.manifest_repository import MongoManifestRepository
from ragcore.adapters.storage.mongo.run_summary_repository import MongoRunSummaryRepository
from ragcore.adapters.storage.mongo.schemas import ensure_data_indexes, ensure_meta_indexes
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
from ragcore.adapters.telemetry.registry_aware import RegistryAwareTelemetry
from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.pipeline_context import PipelineContext
from ragcore.config.settings import get_embedding_settings, get_settings
from ragcore.core.models.audit import build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId
from ragcore.core.telemetry_events import (
    EVENT_CATALOG,
    PIPELINE_RUN_COMPLETED,
    PIPELINE_RUN_FAILED,
    PIPELINE_RUN_STARTED,
)
from ragcore.core.services.telemetry_registry import TelemetryRegistry
from ragcore.utils.async_utils import close_loop, run_async
from ragcore.sources.legi.chunking import LegiChunker
from ragcore.sources.legi.file_connector import LegiFileConnector
from ragcore.sources.legi.parser import LegiParser
from ragcore.sources.legi.relations import LegiRelationExtractor


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

    @hook_impl
    def before_pipeline_run(self, run_params: dict, catalog: DataCatalog) -> None:
        settings = get_settings()
        embedding_settings = get_embedding_settings()

        # Charger les paramètres Kedro (parameters.yml)
        try:
            params = catalog.load("parameters")
        except Exception:
            # Si les paramètres ne sont pas disponibles, utiliser des valeurs par défaut
            params = {}

        # Extraire les paramètres de chunking et Qdrant
        chunking_params = params.get("formatting", {}).get("chunking", {})
        chunk_size = chunking_params.get("chunk_size", 1000)
        chunk_overlap = chunking_params.get("chunk_overlap", 100)

        qdrant_params = params.get("exportation", {}).get("qdrant", {})
        qdrant_collection = qdrant_params.get("collection", "chunks")

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
        run_async(ensure_data_indexes(mongo_client[data_db]))
        run_async(ensure_meta_indexes(mongo_client[meta_db]))

        # Repositories — data DB (LEGIFRANCE) vs meta DB (MURPHY_META)
        doc_repo = MongoDocumentRepository(mongo_client, data_db)
        manifest_repo = MongoManifestRepository(mongo_client, data_db)
        audit_repo = MongoAuditRepository(mongo_client, meta_db)
        summary_repo = MongoRunSummaryRepository(mongo_client, meta_db)
        graph_repo = Neo4jGraphRepository(neo4j_driver)
        vector_repo = QdrantVectorRepository(qdrant_client, qdrant_collection, embedding_settings.dimension)

        # Pipeline context (created early so telemetry adapters can use the run_id)
        owner_id = (run_params.get("extra_params") or {}).get("owner_id", settings.owner_id)
        self._context = PipelineContext.create(
            owner_id=OwnerId(owner_id),
            source=SourceName.LEGI,
        )

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
                "mongo": MongoAuditTelemetryAdapter(audit_repo),
                "aggregate": self._aggregator,
            },
        )

        # Use case
        ingest_use_case = IngestDocumentUseCase(
            document_repo=doc_repo,
            graph_repo=graph_repo,
            vector_repo=vector_repo,
            manifest_repo=manifest_repo,
            telemetry=self._telemetry,
        )

        # LEGI source components
        connector = LegiFileConnector(settings.xml_source_path)
        parser = LegiParser()
        chunker = LegiChunker(max_chunk_size=chunk_size, overlap=chunk_overlap)
        relation_extractor = LegiRelationExtractor()

        # Embedding adapter
        if embedding_settings.provider == "local":
            embedder: object = LocalEmbedder(
                model_name=embedding_settings.model_name,
                dimension=embedding_settings.dimension,
            )
        elif embedding_settings.provider == "noop":
            embedder = NoopEmbedder(dimension=embedding_settings.dimension)
        else:
            embedder = OpenAIEmbedder(
                api_key=embedding_settings.api_key,
                model_name=embedding_settings.model_name,
                dimension=embedding_settings.dimension,
                batch_size=embedding_settings.batch_size,
                base_url=embedding_settings.service_url,
            )

        # Populate catalog for node injection
        catalog.save("connector", connector)
        catalog.save("parser", parser)
        catalog.save("chunker", chunker)
        catalog.save("embedder", embedder)
        catalog.save("relation_extractor", relation_extractor)
        catalog.save("ingest_use_case", ingest_use_case)
        catalog.save("manifest_repo", manifest_repo)
        catalog.save("doc_repo", doc_repo)
        catalog.save("graph_repo", graph_repo)
        catalog.save("vector_repo", vector_repo)
        catalog.save("pipeline_context", self._context)
        catalog.save("telemetry", self._telemetry)

        self._telemetry.emit(
            build_event(
                event_type=PIPELINE_RUN_STARTED,
                run_id=self._context.run_id,
                owner_id=self._context.owner_id,
                source=self._context.source,
                payload={"pipeline": run_params.get("pipeline_name", "__default__")},
            )
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
        run_async(self._summary_repo.upsert(summary))

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
        close_loop()

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
        close_loop()
