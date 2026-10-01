"""Persistance des collisions de métadonnées (ADR-049).

Un document par (document, clé) : ``run_id``, ``source``, ``identifier``, ``key``,
``values``. La collection est VIDÉE puis réécrite à chaque run, sans lien avec
``nuke_all`` : elle montre les collisions du dernier run, rien de plus. Pas d'index : on
la lit pour analyser, on ne l'interroge pas en production.
"""

from collections.abc import Sequence

from pymongo.errors import PyMongoError

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.exceptions import CollisionRecordingError
from ragcore.core.models.collision import Collision
from ragcore.core.models.identifiers import RunId

__all__ = ["COLLISIONS_COLLECTION", "MongoCollisionRepository"]

COLLISIONS_COLLECTION = "collisions"


class MongoCollisionRepository:
    """Implémentation Mongo de ``CollisionRepository``."""

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = COLLISIONS_COLLECTION,
    ) -> None:
        self._collection = client[db_name][collection]

    async def replace(self, run_id: RunId, collisions: Sequence[Collision]) -> None:
        records = [
            {"run_id": run_id, **collision.model_dump(mode="json")}
            for collision in collisions
        ]
        try:
            await self._collection.delete_many({})
            if records:
                await self._collection.insert_many(records)
        except PyMongoError as exc:
            raise CollisionRecordingError(
                f"Écriture de {len(records)} collision(s) du run {run_id} impossible :"
                f" {exc}"
            ) from exc
