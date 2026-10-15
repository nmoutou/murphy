from __future__ import annotations

import logging
from dataclasses import dataclass

from ragcore.adapters.storage.mongo.client import MongoDatabase
from ragcore.adapters.storage.mongo.schemas import (
    reset_data_collections,
    reset_problem_collections,
)
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.opensearch.search_index import OpenSearchSearchIndex
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.transit_repository import TransitRelationRepository

__all__ = ["NukeTargets", "nuke_all_node"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NukeTargets:
    """Ce que ``nukeAll`` efface, posé au catalogue par le hook. La base méta n'y est
    pas."""

    data_db: MongoDatabase
    problems_db: MongoDatabase
    graph: Neo4jGraphRepository
    search_index: OpenSearchSearchIndex
    transit: TransitRelationRepository


def nuke_all_node(
    targets: NukeTargets, nuke_all: bool, pipeline_runtime: AsyncRuntime
) -> dict[str, bool]:
    """Efface toutes les données de toutes les bases quand ``nuke_all=true``.

    - Mongo : les collections déclarées de la base de données et de la base des
      problèmes ;
    - Neo4j : le graphe entier ;
    - OpenSearch : l'index du run.

    La base méta (bilans de run) est préservée. Hors ``ENVIRONMENT=dev``, ``nuke_all``
    arrive ici à ``False`` (``resolve_dev_settings``).

    ``transit_relations`` est vidée dans tous les cas, avant la phase 1 : les restes
    d'un run en échec ne contiennent rien que ce run ne reproduise (ADR-034 §4).
    """
    pipeline_runtime.run(targets.transit.clear())
    if not nuke_all:
        # L'index doit exister avant le pool : créé par les workers, il les mettrait en
        # course
        pipeline_runtime.run(targets.search_index.ensure_index())
        return {"mongodb": False, "neo4j": False, "opensearch": False}

    logger.warning(
        "nuke_all activé (ENVIRONMENT=dev) : effacement de TOUTES les données de TOUTES les bases"
    )
    _drop_mongo(targets, pipeline_runtime)

    logger.warning("nuke_all Neo4j : suppression complète du graphe")
    pipeline_runtime.run(targets.graph.drop_all())

    logger.warning("nuke_all OpenSearch : suppression de l'index du run")
    pipeline_runtime.run(targets.search_index.drop_index())

    pipeline_runtime.run(targets.search_index.ensure_index())
    return {"mongodb": True, "neo4j": True, "opensearch": True}


def _drop_mongo(targets: NukeTargets, pipeline_runtime: AsyncRuntime) -> None:
    logger.warning(
        "nuke_all Mongo : suppression des collections de %s et de %s",
        targets.data_db.name,
        targets.problems_db.name,
    )
    pipeline_runtime.run(reset_data_collections(targets.data_db))
    pipeline_runtime.run(reset_problem_collections(targets.problems_db))
