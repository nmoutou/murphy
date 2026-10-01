from pymongo import ASCENDING, IndexModel

from ragcore.adapters.storage.mongo.client import MongoDatabase
from ragcore.adapters.storage.mongo.pending_repository import (
    PENDING_RELATIONS_COLLECTION,
)

_DATA_INDEXES: dict[str, list[IndexModel]] = {
    "documents": [
        # `identifier` est la chaîne sérialisée (cf. MongoDocumentRepository),
        # pas un sous-document : indexer
        # `identifier.raw` indexerait `null` pour tout le monde.
        IndexModel(
            [("identifier", ASCENDING)],
            unique=True,
            name="uq_identifier",
        ),
        IndexModel([("source", ASCENDING)], name="idx_source"),
    ],
    # Pas de TTL : une pendante attend, elle n'expire pas.
    PENDING_RELATIONS_COLLECTION: [
        # L'index qui fait de `upsert_many` une UNION. Sans lui, revoir la même
        # pendante à chaque run empilerait les doublons, et le backlog
        # mesurerait le nombre de runs au lieu du nombre de trous.
        IndexModel(
            [
                ("source_id", ASCENDING),
                ("target_id", ASCENDING),
                ("relation_type", ASCENDING),
            ],
            unique=True,
            name="uq_pending_source_target_type",
        ),
        # Le rejeu ciblé interroge `target_id` : sans cet index, il ferait un
        # COLLSCAN du backlog — exactement le coût que §13 refuse.
        IndexModel([("target_id", ASCENDING)], name="idx_pending_target"),
    ],
}
"""Les index de la base de données (défaut : MURPHY_DATA), par collection."""

_META_INDEXES: dict[str, list[IndexModel]] = {
    "run_summaries": [
        IndexModel(
            [("run_id", ASCENDING)],
            unique=True,
            name="uq_run_summary_run_id",
        ),
        IndexModel([("started_at", ASCENDING)], name="idx_run_summary_started_at"),
    ],
}
"""Les index de la base méta (défaut : MURPHY_META), par collection."""


async def ensure_data_indexes(db: MongoDatabase) -> None:
    """Pose les index de la base de données (``_DATA_INDEXES``)."""
    await _create_indexes(db, _DATA_INDEXES)


async def ensure_meta_indexes(db: MongoDatabase) -> None:
    """Pose les index de la base méta (``_META_INDEXES``)."""
    await _create_indexes(db, _META_INDEXES)


async def reset_data_collections(db: MongoDatabase) -> None:
    """Droppe chaque collection de ``_DATA_INDEXES``, puis repose leurs index.

    Dropper une collection détruit ses index avec elle : sans la seconde moitié, le run
    réécrirait dans des collections nues, et ni l'unicité de `identifier` ni l'union des
    pendantes ne protégeraient plus rien — en silence. Seules les collections déclarées
    sont touchées : une base méta configurée sous le même nom resterait intacte.
    """
    for collection in _DATA_INDEXES:
        await db.drop_collection(collection)
    await ensure_data_indexes(db)


async def _create_indexes(
    db: MongoDatabase, indexes: dict[str, list[IndexModel]]
) -> None:
    for collection, models in indexes.items():
        await db[collection].create_indexes(models)
