from pymongo import ASCENDING, IndexModel

from ragcore.adapters.storage.mongo.client import MongoDatabase
from ragcore.adapters.storage.mongo.pending_repository import (
    PENDING_RELATIONS_COLLECTION,
)
from ragcore.adapters.storage.mongo.unformatted_repository import (
    UNFORMATTED_RELATIONS_COLLECTION,
)

_DATA_INDEXES: dict[str, list[IndexModel]] = {
    "documents": [
        # `identifier` est la chaîne sérialisée, pas un sous-document
        IndexModel(
            [("identifier", ASCENDING)],
            unique=True,
            name="uq_identifier",
        ),
        IndexModel([("source", ASCENDING)], name="idx_source"),
    ],
    # Pas de TTL : une pendante attend, elle n'expire pas.
    PENDING_RELATIONS_COLLECTION: [
        # Fait de `upsert_many` une union : sans lui, les doublons s'empileraient
        IndexModel(
            [
                ("source_id", ASCENDING),
                ("target_id", ASCENDING),
                ("relation_type", ASCENDING),
            ],
            unique=True,
            name="uq_pending_source_target_type",
        ),
        # Le rejeu ciblé interroge `target_id`
        IndexModel([("target_id", ASCENDING)], name="idx_pending_target"),
    ],
    # Pas de TTL non plus : une relation non formatée attend sa résolution.
    UNFORMATTED_RELATIONS_COLLECTION: [
        # Son préfixe `source_id` sert aussi la compensation (`delete_first_seen`)
        IndexModel(
            [
                ("source_id", ASCENDING),
                ("target_text", ASCENDING),
                ("relation_type", ASCENDING),
                ("sens", ASCENDING),
            ],
            unique=True,
            name="uq_unformatted_source_text_type_sens",
        ),
    ],
}
"""Par collection, dans la base de données."""

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
"""Par collection, dans la base méta."""


async def ensure_data_indexes(db: MongoDatabase) -> None:
    await _create_indexes(db, _DATA_INDEXES)


async def ensure_meta_indexes(db: MongoDatabase) -> None:
    await _create_indexes(db, _META_INDEXES)


async def reset_data_collections(db: MongoDatabase) -> None:
    """Droppe chaque collection de ``_DATA_INDEXES``, puis repose leurs index, que le
    drop emporte. Seules les collections déclarées sont touchées : une base méta
    configurée sous le même nom resterait intacte.
    """
    for collection in _DATA_INDEXES:
        await db.drop_collection(collection)
    await ensure_data_indexes(db)


async def _create_indexes(
    db: MongoDatabase, indexes: dict[str, list[IndexModel]]
) -> None:
    for collection, models in indexes.items():
        await db[collection].create_indexes(models)
