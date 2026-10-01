"""Les clients d'infrastructure et les dépôts du run.

Le code est partagé, pas les instances : un client est lié à la boucle qui l'appelle
en premier. Le hook et chaque worker appellent ``open_clients`` depuis leur runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

import neo4j
from qdrant_client import AsyncQdrantClient

from ragcore.adapters.config.settings import InfraSettings
from ragcore.adapters.storage.mongo.client import MongoClient, create_mongo_client
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
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
from ragcore.adapters.storage.mongo.unformatted_repository import (
    MongoUnformattedRelationRepository,
)
from ragcore.adapters.storage.neo4j.client import create_neo4j_driver
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.neo4j.schema import ensure_graph_constraints
from ragcore.adapters.storage.qdrant.client import create_qdrant_client
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.application.ingest_document import IngestionStores
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.orchestration.kedro.run_plan import RunPlan

__all__ = [
    "InfraClients",
    "MetaStores",
    "ensure_indexes",
    "open_clients",
    "open_document_stores",
    "open_meta_stores",
]


@dataclass(frozen=True)
class InfraClients:
    mongo: MongoClient
    neo4j: neo4j.AsyncDriver
    qdrant: AsyncQdrantClient


@dataclass(frozen=True)
class MetaStores:
    summaries: MongoRunSummaryRepository


def open_clients(settings: InfraSettings) -> InfraClients:
    """Aucun ne se connecte à la construction."""
    qdrant_api_key = (
        settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None
    )
    return InfraClients(
        mongo=create_mongo_client(settings.mongodb_uri),
        neo4j=create_neo4j_driver(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password.get_secret_value(),
        ),
        qdrant=create_qdrant_client(settings.qdrant_url, qdrant_api_key),
    )


def ensure_indexes(
    clients: InfraClients, settings: InfraSettings, runtime: AsyncRuntime
) -> None:
    runtime.run(ensure_data_indexes(clients.mongo[settings.mongodb_data_db_name]))
    runtime.run(ensure_meta_indexes(clients.mongo[settings.mongodb_meta_db_name]))
    runtime.run(ensure_graph_constraints(clients.neo4j))


def open_document_stores(
    clients: InfraClients, settings: InfraSettings, plan: RunPlan, vector_size: int
) -> IngestionStores:
    """``vector_size`` est la dimension mesurée auprès de TEI."""
    data_db = settings.mongodb_data_db_name
    return IngestionStores(
        documents=MongoDocumentRepository(
            clients.mongo, data_db, include_path=plan.include_path
        ),
        graph=Neo4jGraphRepository(clients.neo4j, plan.node_hydration),
        vectors=QdrantVectorRepository(clients.qdrant, plan.collection, vector_size),
        pending=MongoPendingRelationRepository(clients.mongo, data_db),
        unformatted=MongoUnformattedRelationRepository(clients.mongo, data_db),
    )


def open_meta_stores(clients: InfraClients, settings: InfraSettings) -> MetaStores:
    return MetaStores(
        summaries=MongoRunSummaryRepository(
            clients.mongo, settings.mongodb_meta_db_name
        ),
    )
