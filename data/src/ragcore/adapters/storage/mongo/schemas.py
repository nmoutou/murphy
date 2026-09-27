from pymongo import ASCENDING, IndexModel

from ragcore.adapters.storage.mongo.client import MongoDatabase

_DATA_INDEXES: dict[str, list[IndexModel]] = {
    "documents": [
        # `identifier` est la chaîne sérialisée `{kind}:{raw}` (cf.
        # MongoDocumentRepository), pas un sous-document : indexer
        # `identifier.raw` indexerait `null` pour tout le monde.
        IndexModel(
            [("identifier", ASCENDING), ("owner_id", ASCENDING)],
            unique=True,
            name="uq_identifier_owner",
        ),
        IndexModel(
            [("source", ASCENDING), ("owner_id", ASCENDING)],
            name="idx_source_owner",
        ),
    ],
    "manifest": [
        # Le manifest est append-only : plusieurs entrées par document, une
        # par run (`last_for_identifier` trie par processed_at DESC). Un index
        # unique le casserait au deuxième run. C'est un index de lookup.
        # Le champ écrit s'appelle `identifier_serialized` (cf.
        # MongoManifestRepository), et il est absent des entrées de rejet.
        IndexModel(
            [("identifier_serialized", ASCENDING), ("owner_id", ASCENDING)],
            name="idx_manifest_identifier_owner",
            sparse=True,
        ),
        # Les rejets n'ont pas d'identifier : ils ne sont retrouvables que
        # par leur chemin source.
        IndexModel(
            [("source_path", ASCENDING), ("owner_id", ASCENDING)],
            name="idx_manifest_source_path_owner",
        ),
    ],
}
"""Les index de la base de données (défaut : LEGIFRANCE), par collection."""

_META_INDEXES: dict[str, list[IndexModel]] = {
    # Pas de TTL : rétention infinie de l'audit.
    "meta_audit_events": [
        IndexModel(
            [("owner_id", ASCENDING), ("occurred_at", ASCENDING)],
            name="idx_audit_owner_occurred_at",
        ),
        IndexModel(
            [("document_id", ASCENDING), ("occurred_at", ASCENDING)],
            name="idx_audit_document_occurred_at",
        ),
        IndexModel([("run_id", ASCENDING)], name="idx_audit_run_id"),
        IndexModel([("event_type", ASCENDING)], name="idx_audit_event_type"),
    ],
    "meta_run_summaries": [
        IndexModel(
            [("run_id", ASCENDING)],
            unique=True,
            name="uq_run_summary_run_id",
        ),
        IndexModel([("started_at", ASCENDING)], name="idx_run_summary_started_at"),
    ],
    # Pas de TTL non plus : une pendante attend, elle n'expire pas.
    "meta_pending_relations": [
        # L'index qui fait de `upsert_many` une UNION. Sans lui, revoir la même
        # pendante à chaque run empilerait les doublons, et le backlog
        # mesurerait le nombre de runs au lieu du nombre de trous.
        IndexModel(
            [
                ("owner_id", ASCENDING),
                ("source_id", ASCENDING),
                ("target_id", ASCENDING),
                ("relation_type", ASCENDING),
            ],
            unique=True,
            name="uq_pending_owner_source_target_type",
        ),
        # Le rejeu ciblé interroge (owner_id, target_id) : sans cet index, il
        # ferait un COLLSCAN du backlog — exactement le coût que §13 refuse.
        IndexModel(
            [("owner_id", ASCENDING), ("target_id", ASCENDING)],
            name="idx_pending_owner_target",
        ),
    ],
}
"""Les index de la base méta (défaut : MURPHY_META), par collection."""


async def ensure_data_indexes(db: MongoDatabase) -> None:
    """Pose les index de la base de données (``_DATA_INDEXES``)."""
    await _create_indexes(db, _DATA_INDEXES)


async def ensure_meta_indexes(db: MongoDatabase) -> None:
    """Pose les index de la base méta (``_META_INDEXES``)."""
    await _create_indexes(db, _META_INDEXES)


async def _create_indexes(
    db: MongoDatabase, indexes: dict[str, list[IndexModel]]
) -> None:
    for collection, models in indexes.items():
        await db[collection].create_indexes(models)
