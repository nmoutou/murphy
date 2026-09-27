"""Les clients d'infrastructure et les dépôts du run — écrits UNE fois.

Le hook et chaque worker de la phase 1 ouvrent leurs clients ici. Le code est partagé,
**pas les instances** (§11) : un client Motor/Neo4j/Qdrant est lié à la boucle qui
l'appelle en premier. Réutiliser ceux du hook les lierait à la boucle du hook, et tous
les workers échoueraient sauf un. Chacun appelle donc ``open_clients`` depuis son runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

import neo4j
from qdrant_client import AsyncQdrantClient

from ragcore.adapters.config.settings import InfraSettings
from ragcore.adapters.storage.mongo.audit_repository import MongoAuditRepository
from ragcore.adapters.storage.mongo.client import MongoClient, create_mongo_client
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.manifest_repository import MongoManifestRepository
from ragcore.adapters.storage.mongo.pending_repository import (
    MongoPendingRelationRepository,
)
from ragcore.adapters.storage.mongo.published_collection_repository import (
    MongoPublishedCollectionRepository,
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
    """La base méta : audit, bilans, pointeur publié, relations en attente."""

    audit: MongoAuditRepository
    summaries: MongoRunSummaryRepository
    published: MongoPublishedCollectionRepository
    pending: MongoPendingRelationRepository


def open_clients(settings: InfraSettings) -> InfraClients:
    """Ouvre les trois clients. Aucun ne se connecte à la construction."""
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
    """Pose les index Mongo des bases de données et méta."""
    runtime.run(ensure_data_indexes(clients.mongo[settings.mongodb_data_db_name]))
    runtime.run(ensure_meta_indexes(clients.mongo[settings.mongodb_meta_db_name]))


def open_document_stores(
    clients: InfraClients, settings: InfraSettings, plan: RunPlan
) -> IngestionStores:
    """Les dépôts que l'ingestion écrit, sur la collection et l'hydratation du plan.

    Le hook en ouvre un jeu (maintenance, phase 2), chaque worker de la phase 1 le sien.
    """
    data_db = settings.mongodb_data_db_name
    return IngestionStores(
        documents=MongoDocumentRepository(clients.mongo, data_db),
        manifest=MongoManifestRepository(clients.mongo, data_db),
        graph=Neo4jGraphRepository(clients.neo4j, plan.node_hydration),
        vectors=QdrantVectorRepository(
            clients.qdrant, plan.collection, plan.workflow.embedding.dimension
        ),
    )


def open_meta_stores(clients: InfraClients, settings: InfraSettings) -> MetaStores:
    meta_db = settings.mongodb_meta_db_name
    return MetaStores(
        audit=MongoAuditRepository(clients.mongo, meta_db),
        summaries=MongoRunSummaryRepository(clients.mongo, meta_db),
        published=MongoPublishedCollectionRepository(clients.mongo, meta_db),
        pending=MongoPendingRelationRepository(clients.mongo, meta_db),
    )
