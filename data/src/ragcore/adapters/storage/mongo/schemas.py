from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel


async def ensure_data_indexes(db: AsyncIOMotorDatabase) -> None:
    """Indexes pour la DB de données (défaut : LEGIFRANCE).

    - documents : unique (identifier, owner_id) + (source, owner_id) + sparse eli.raw
    - manifest  : unique (identifier, owner_id)
    """
    documents = db["documents"]
    await documents.create_indexes(
        [
            IndexModel(
                [("identifier.raw", ASCENDING), ("owner_id", ASCENDING)],
                unique=True,
                name="uq_identifier_owner",
            ),
            IndexModel(
                [("source", ASCENDING), ("owner_id", ASCENDING)],
                name="idx_source_owner",
            ),
            IndexModel(
                [("eli.raw", ASCENDING)],
                name="idx_eli_raw",
                sparse=True,
            ),
        ]
    )

    manifest = db["manifest"]
    await manifest.create_indexes(
        [
            IndexModel(
                [("identifier.raw", ASCENDING), ("owner_id", ASCENDING)],
                unique=True,
                name="uq_manifest_identifier_owner",
            ),
        ]
    )


async def ensure_meta_indexes(db: AsyncIOMotorDatabase) -> None:
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
