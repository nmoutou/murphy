from __future__ import annotations

import logging
from typing import Any

from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.manifest_repository import MongoManifestRepository
from ragcore.adapters.storage.mongo.schemas import ensure_data_indexes
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import MAINTENANCE_FORCE_DROP_EXECUTED

logger = logging.getLogger(__name__)


def force_drop_node(  # noqa: PLR0913 — le drop touche 3 stores + leurs 3 paramètres ; les grouper cacherait ce qu'il efface
    doc_repo: MongoDocumentRepository,
    manifest_repo: MongoManifestRepository,
    graph_repo: Neo4jGraphRepository,
    vector_repo: QdrantVectorRepository,
    mongodb_params: dict[str, Any],
    neo4j_params: dict[str, Any],
    qdrant_params: dict[str, Any],
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
    pipeline_runtime: AsyncRuntime,
) -> dict[str, bool]:
    """Wipe stores entirely when `force_drop=true`. Runs at the head of ingestion."""
    dropped: dict[str, bool] = {"mongodb": False, "neo4j": False, "qdrant": False}

    if mongodb_params.get("force_drop"):
        logger.warning("force_drop MongoDB activé : suppression des collections documents + manifest")
        pipeline_runtime.run(doc_repo.drop_collection())
        pipeline_runtime.run(manifest_repo.drop_collection())
        # Dropper une collection détruit ses index avec elle. Ceux que le hook a
        # posés en `before_pipeline_run` viennent de disparaître : sans ce rappel,
        # tout le run réécrit dans des collections nues, et l'unicité de
        # (identifier, owner_id) ne protège plus rien — en silence.
        pipeline_runtime.run(ensure_data_indexes(doc_repo.database))
        dropped["mongodb"] = True

    if neo4j_params.get("force_drop"):
        logger.warning("force_drop Neo4j activé : suppression complète du graphe")
        pipeline_runtime.run(graph_repo.drop_all())
        dropped["neo4j"] = True

    if qdrant_params.get("force_drop"):
        logger.warning("force_drop Qdrant activé : suppression de la collection")
        pipeline_runtime.run(vector_repo.drop_collection())
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
