"""Persistance du pointeur de collection.

``replace_one`` sur une clé FIXE (``POINTER_KEY``) : le pointeur est un singleton. Un
`insert` produirait un journal, et « quelle collection fait foi ? » redeviendrait une
question — à l'intérieur même du mécanisme censé y répondre.
"""

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.published_collection import POINTER_KEY, PublishedCollection

__all__ = ["MongoPublishedCollectionRepository"]


class MongoPublishedCollectionRepository:
    """Implémentation Mongo de ``PublishedCollectionRepository``."""

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = "meta_published_collection",
    ) -> None:
        self._collection = client[db_name][collection]

    async def publish(self, published: PublishedCollection) -> None:
        await self._collection.replace_one(
            {"key": POINTER_KEY},
            published.model_dump(mode="json"),
            upsert=True,
        )

    async def get(self) -> PublishedCollection | None:
        doc = await self._collection.find_one({"key": POINTER_KEY})
        if doc is None:
            return None
        doc.pop("_id", None)
        return PublishedCollection(**doc)
