"""Le registre des relations pendantes.

L'union est idempotente grâce à l'index unique sur le triplet : ``$setOnInsert`` fige
``first_seen_run``, ``$set`` fait avancer ``last_seen_run``.
"""

from collections.abc import Iterator, Sequence
from typing import TypeVar

from pymongo import UpdateOne

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.pending import PendingKey, PendingRelation

__all__ = ["PENDING_RELATIONS_COLLECTION", "MongoPendingRelationRepository"]

PENDING_RELATIONS_COLLECTION = "pending_relations"
"""Dans la base de données, pas la méta."""

_QUERY_CHUNK = 10_000
"""Les valeurs d'un ``$in`` ou d'un ``$or`` : une requête Mongo ne dépasse pas 16 Mo, et
le delta d'un run complet compte ~2,1 M identifiants (ADR-034 §7)."""

_T = TypeVar("_T")


def _chunks(values: Sequence[_T]) -> Iterator[Sequence[_T]]:
    for start in range(0, len(values), _QUERY_CHUNK):
        yield values[start : start + _QUERY_CHUNK]


def _key_filter(key: PendingKey) -> dict[str, object]:
    """Celui de l'index unique."""
    return {
        "source_id": key.source_id,
        "target_id": key.target_id,
        "relation_type": key.relation_type,
    }


class MongoPendingRelationRepository:
    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = PENDING_RELATIONS_COLLECTION,
    ) -> None:
        self._collection = client[db_name][collection]

    async def upsert_many(self, pendings: list[PendingRelation]) -> None:
        if not pendings:
            return

        operations = []
        for pending in pendings:
            document = pending.model_dump(mode="json")
            # Hors du $set : first_seen_run ne doit pas reculer quand la pendante est revue
            first_seen_run = document.pop("first_seen_run")
            operations.append(
                UpdateOne(
                    _key_filter(pending.key),
                    {
                        "$set": document,
                        "$setOnInsert": {"first_seen_run": first_seen_run},
                    },
                    upsert=True,
                )
            )

        await self._collection.bulk_write(operations, ordered=False)

    async def promotable_for(self, written_node_ids: set[str]) -> list[PendingRelation]:
        promotable: list[PendingRelation] = []
        for chunk in _chunks(list(written_node_ids)):
            cursor = self._collection.find(
                {"target_id": {"$in": list(chunk)}}, {"_id": 0}
            )
            promotable.extend(
                [PendingRelation.model_validate(doc) async for doc in cursor]
            )
        return promotable

    async def delete_many(self, keys: list[PendingKey]) -> None:
        for chunk in _chunks(keys):
            await self._collection.delete_many(
                {"$or": [_key_filter(key) for key in chunk]}
            )

    async def count(self) -> int:
        return await self._collection.count_documents({})
