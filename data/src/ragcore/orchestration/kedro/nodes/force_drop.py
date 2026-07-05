from __future__ import annotations

import logging
from typing import Any

from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.manifest_repository import MongoManifestRepository
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.application.pipeline_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.telemetry_events import MAINTENANCE_FORCE_DROP_EXECUTED
from ragcore.core.ports.telemetry import TelemetryPort

from ._async_utils import run_async

logger = logging.getLogger(__name__)


def force_drop_node(
    doc_repo: MongoDocumentRepository,
    manifest_repo: MongoManifestRepository,
    graph_repo: Neo4jGraphRepository,
    vector_repo: QdrantVectorRepository,
    mongodb_params: dict[str, Any],
    neo4j_params: dict[str, Any],
    qdrant_params: dict[str, Any],
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
) -> dict[str, bool]:
    """Wipe stores entirely when `force_drop=true`. Runs at the head of ingestion."""
    dropped: dict[str, bool] = {"mongodb": False, "neo4j": False, "qdrant": False}

    if mongodb_params.get("force_drop"):
        logger.warning("force_drop MongoDB activé : suppression des collections documents + manifest")
        run_async(doc_repo.drop_collection())
        run_async(manifest_repo.drop_collection())
        dropped["mongodb"] = True

    if neo4j_params.get("force_drop"):
        logger.warning("force_drop Neo4j activé : suppression complète du graphe")
        run_async(graph_repo.drop_all())
        dropped["neo4j"] = True

    if qdrant_params.get("force_drop"):
        logger.warning("force_drop Qdrant activé : suppression de la collection")
        run_async(vector_repo.drop_collection())
        dropped["qdrant"] = True

    telemetry.emit(
        build_event(
            event_type=MAINTENANCE_FORCE_DROP_EXECUTED,
            run_id=pipeline_context.run_id,
            owner_id=pipeline_context.owner_id,
            source=pipeline_context.source,
            payload=dropped,
        )
    )
    return dropped
