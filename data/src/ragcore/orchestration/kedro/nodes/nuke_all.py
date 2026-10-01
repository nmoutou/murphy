from __future__ import annotations

import logging

from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.schemas import reset_data_collections
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.core.ports.runtime import AsyncRuntime

logger = logging.getLogger(__name__)


def nuke_all_node(
    doc_repo: MongoDocumentRepository,
    graph_repo: Neo4jGraphRepository,
    vector_repo: QdrantVectorRepository,
    nuke_all: bool,
    pipeline_runtime: AsyncRuntime,
) -> dict[str, bool]:
    """Efface toutes les données de toutes les bases quand ``nuke_all=true``.

    - Mongo : `documents`, `pending_relations` et `unformatted_relations`, qui
      pointent vers les nœuds effacés ;
    - Neo4j : le graphe entier ;
    - Qdrant : toutes les collections du store, pas seulement celle du run.

    La base méta (bilans de run) est préservée. Hors ``ENVIRONMENT=dev``, ``nuke_all``
    arrive ici à ``False`` (``resolve_dev_settings``).
    """
    if not nuke_all:
        # La collection doit exister avant le pool : créée par les workers, elle les
        # mettrait en course (`409`)
        pipeline_runtime.run(vector_repo.ensure_collection())
        return {"mongodb": False, "neo4j": False, "qdrant": False}

    logger.warning(
        "nuke_all activé (ENVIRONMENT=dev) : effacement de TOUTES les données de TOUTES les bases"
    )
    _drop_mongo(doc_repo, pipeline_runtime)

    logger.warning("nuke_all Neo4j : suppression complète du graphe")
    pipeline_runtime.run(graph_repo.drop_all())

    logger.warning("nuke_all Qdrant : suppression de TOUTES les collections du store")
    pipeline_runtime.run(vector_repo.drop_all_collections())

    dropped: dict[str, bool] = {"mongodb": True, "neo4j": True, "qdrant": True}

    pipeline_runtime.run(vector_repo.ensure_collection())
    return dropped


def _drop_mongo(
    doc_repo: MongoDocumentRepository, pipeline_runtime: AsyncRuntime
) -> None:
    logger.warning(
        "nuke_all Mongo : suppression des collections documents, pending_relations"
        " et unformatted_relations"
    )
    pipeline_runtime.run(reset_data_collections(doc_repo.database))
