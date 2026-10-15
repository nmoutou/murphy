from pymongo import ASCENDING, IndexModel

from ragcore.adapters.storage.mongo.client import MongoDatabase
from ragcore.adapters.storage.mongo.pending_repository import (
    PENDING_RELATIONS_COLLECTION,
)
from ragcore.adapters.storage.mongo.problem_repository import (
    COLLISIONS_COLLECTION,
    MISMATCH_COLLECTION,
    SUPERSEDED_COLLECTION,
    UNREADABLE_COLLECTION,
)
from ragcore.adapters.storage.mongo.statistics_repository import STATISTICS_COLLECTION
from ragcore.adapters.storage.mongo.transit_repository import (
    TRANSIT_RELATIONS_COLLECTION,
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
    # Non unique : une arête déclarée par deux documents donne deux lignes, que la
    # réduction dédoublonne. Son préfixe `run_id` sert aussi la compensation.
    TRANSIT_RELATIONS_COLLECTION: [
        IndexModel(
            [
                ("run_id", ASCENDING),
                ("relation_type", ASCENDING),
                ("source_id", ASCENDING),
            ],
            name="idx_transit_run_type_source",
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
    STATISTICS_COLLECTION: [
        IndexModel(
            [("run_id", ASCENDING)],
            unique=True,
            name="uq_statistics_run_id",
        ),
    ],
}
"""Par collection, dans la base méta."""

_PROBLEMS_INDEXES: dict[str, list[IndexModel]] = {
    # Pas de TTL : une relation non formatée attend sa résolution.
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
    COLLISIONS_COLLECTION: [
        IndexModel(
            [("run_id", ASCENDING), ("source", ASCENDING), ("reason", ASCENDING)],
            name="idx_collisions_run_source_reason",
        ),
        IndexModel([("identifier", ASCENDING)], name="idx_collisions_identifier"),
    ],
    SUPERSEDED_COLLECTION: [
        IndexModel(
            [("run_id", ASCENDING), ("source", ASCENDING)],
            name="idx_superseded_run_source",
        ),
        IndexModel([("identifier", ASCENDING)], name="idx_superseded_identifier"),
    ],
    UNREADABLE_COLLECTION: [
        IndexModel(
            [("run_id", ASCENDING), ("source", ASCENDING)],
            name="idx_unreadable_run_source",
        ),
    ],
    MISMATCH_COLLECTION: [
        IndexModel(
            [("run_id", ASCENDING), ("source", ASCENDING)],
            name="idx_mismatch_run_source",
        ),
    ],
}
"""Par collection, dans la base des problèmes."""


async def ensure_data_indexes(db: MongoDatabase) -> None:
    await _create_indexes(db, _DATA_INDEXES)


async def ensure_meta_indexes(db: MongoDatabase) -> None:
    await _create_indexes(db, _META_INDEXES)


async def ensure_problems_indexes(db: MongoDatabase) -> None:
    await _create_indexes(db, _PROBLEMS_INDEXES)


async def reset_data_collections(db: MongoDatabase) -> None:
    await _reset_collections(db, _DATA_INDEXES)


async def reset_problem_collections(db: MongoDatabase) -> None:
    await _reset_collections(db, _PROBLEMS_INDEXES)


async def _reset_collections(
    db: MongoDatabase, indexes: dict[str, list[IndexModel]]
) -> None:
    """Droppe chaque collection déclarée, puis repose ses index, que le drop emporte.
    Seules les collections déclarées sont touchées : une base méta configurée sous le
    même nom resterait intacte.
    """
    for collection in indexes:
        await db.drop_collection(collection)
    await _create_indexes(db, indexes)


async def _create_indexes(
    db: MongoDatabase, indexes: dict[str, list[IndexModel]]
) -> None:
    for collection, models in indexes.items():
        await db[collection].create_indexes(models)
