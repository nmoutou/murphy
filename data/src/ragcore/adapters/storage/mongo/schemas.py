from pymongo import ASCENDING, IndexModel

from ragcore.adapters.storage.mongo.client import MongoDatabase


async def ensure_data_indexes(db: MongoDatabase) -> None:
    """Indexes pour la DB de données (défaut : LEGIFRANCE).

    - documents : unique (identifier, owner_id) + (source, owner_id)
    - manifest  : lookup (identifier_serialized, owner_id) + (source_path, owner_id)
    """
    documents = db["documents"]
    await documents.create_indexes(
        [
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
        ]
    )

    manifest = db["manifest"]
    await manifest.create_indexes(
        [
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
        ]
    )


async def ensure_meta_indexes(db: MongoDatabase) -> None:
    """Indexes for the meta DB (default: MURPHY_META).

    - meta_audit_events      : (owner_id, occurred_at), (document_id, occurred_at), (run_id,)
                               No TTL (infinite retention).
    - meta_run_summaries     : unique (run_id,)
    - meta_pending_relations : unique (owner_id, source_id, target_id, relation_type)
                               No TTL either — a pending edge waits, it does not expire.
    """
    audit_events = db["meta_audit_events"]
    await audit_events.create_indexes(
        [
            IndexModel(
                [("owner_id", ASCENDING), ("occurred_at", ASCENDING)],
                name="idx_audit_owner_occurred_at",
            ),
            IndexModel(
                [("document_id", ASCENDING), ("occurred_at", ASCENDING)],
                name="idx_audit_document_occurred_at",
            ),
            IndexModel(
                [("run_id", ASCENDING)],
                name="idx_audit_run_id",
            ),
            IndexModel(
                [("event_type", ASCENDING)],
                name="idx_audit_event_type",
            ),
        ]
    )

    run_summaries = db["meta_run_summaries"]
    await run_summaries.create_indexes(
        [
            IndexModel(
                [("run_id", ASCENDING)],
                unique=True,
                name="uq_run_summary_run_id",
            ),
            IndexModel(
                [("started_at", ASCENDING)],
                name="idx_run_summary_started_at",
            ),
        ]
    )

    pending_relations = db["meta_pending_relations"]
    await pending_relations.create_indexes(
        [
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
        ]
    )
