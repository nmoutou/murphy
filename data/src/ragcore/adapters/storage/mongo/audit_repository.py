"""Journal d'audit Mongo — append-only, et ASYNC de bout en bout.

Le module perdu qu'il remplace était synchrone : chacune de ses méthodes
enveloppait l'appel Motor dans ``run_async()``, c'est-à-dire dans la boucle
globale. C'est exactement le pattern que le port ``AsyncRuntime`` existe pour
supprimer. Ici, le repository est async parce que Motor l'est ; c'est l'appelant
synchrone (les nœuds Kedro) qui traverse le pont, via SON runtime.
"""

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.audit import AuditEvent

__all__ = ["MongoAuditRepository"]


class MongoAuditRepository:
    """Implémentation Mongo de ``AuditRepository`` (append-only, rétention infinie)."""

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = "meta_audit_events",
    ) -> None:
        self._collection = client[db_name][collection]

    async def append(self, event: AuditEvent) -> None:
        await self._collection.insert_one(event.model_dump(mode="json"))
