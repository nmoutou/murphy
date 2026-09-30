"""Le cache des relations pendantes (§13) — rien n'est jamais jeté.

Trois décisions du cadrage se jouent ici, et chacune est une ligne de Mongo :

1. **Union idempotente.** ``$setOnInsert`` fige ``first_seen_run`` : c'est la date
   de naissance du trou, elle ne bouge jamais. ``$set`` fait avancer
   ``last_seen_run``. Revoir dix fois la même pendante produit UNE entrée — c'est
   l'index unique sur le triplet qui le garantit, pas notre bonne volonté.

2. **Rejeu ciblé.** ``promotable_for`` filtre sur ``target_id ∈ written_node_ids``
   — le delta de LA run. On ne relit jamais le backlog entier : une pendante dont
   la cible n'est pas arrivée cette fois-ci ne peut pas se résoudre, et la
   retenter serait un coût pur qui croît avec l'historique.

3. **Ni TTL, ni ``retry_count``.** Une pendante n'est pas « ratée » : elle attend.
   Un arrêt qui cite une directive jamais ingérée est un lien légitime vers
   l'extérieur du corpus — pas une erreur à faire expirer.
"""

from pymongo import UpdateOne

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.pending import PendingKey, PendingRelation

__all__ = ["MongoPendingRelationRepository"]


def _key_filter(key: PendingKey) -> dict[str, object]:
    """Le triplet — celui de l'index unique."""
    return {
        "source_id": key.source_id,
        "target_id": key.target_id,
        "relation_type": key.relation_type,
    }


class MongoPendingRelationRepository:
    """Implémentation Mongo de ``PendingRelationRepository``."""

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = "meta_pending_relations",
    ) -> None:
        self._collection = client[db_name][collection]

    async def upsert_many(self, pendings: list[PendingRelation]) -> None:
        if not pendings:
            return

        operations = []
        for pending in pendings:
            document = pending.model_dump(mode="json")
            # first_seen_run est posé À LA CRÉATION uniquement : le retirer du $set
            # est ce qui l'empêche de reculer quand la pendante est revue.
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
        if not written_node_ids:
            return []

        cursor = self._collection.find({"target_id": {"$in": list(written_node_ids)}})
        return [
            PendingRelation.model_validate({k: v for k, v in doc.items() if k != "_id"})
            async for doc in cursor
        ]

    async def delete_many(self, keys: list[PendingKey]) -> None:
        if not keys:
            return
        await self._collection.delete_many({"$or": [_key_filter(k) for k in keys]})

    async def count(self) -> int:
        return await self._collection.count_documents({})
