"""Le détail des collisions d'un run, dans la base méta."""

from __future__ import annotations

from datetime import datetime

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_collisions import RunCollisions

from .collision_documents import PART_BUDGET_BYTES, source_documents

__all__ = ["COLLISIONS_COLLECTION", "MongoCollisionRepository"]

COLLISIONS_COLLECTION = "collisions"


class MongoCollisionRepository:
    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        part_budget_bytes: int = PART_BUDGET_BYTES,
    ) -> None:
        self._collection = client[db_name][COLLISIONS_COLLECTION]
        self._part_budget_bytes = part_budget_bytes

    async def replace_run(
        self, run_id: RunId, started_at: datetime, collisions: RunCollisions
    ) -> None:
        documents = [
            document
            for source, found in collisions.by_source().items()
            for document in source_documents(
                {"run_id": run_id, "source": source.value, "started_at": started_at},
                found,
                self._part_budget_bytes,
            )
        ]
        await self._collection.delete_many({"run_id": run_id})
        if documents:
            await self._collection.insert_many(documents)
