"""Implémentation MongoDB du DocumentRepository."""

from ragcore.adapters.storage.mongo.client import MongoClient, MongoDatabase
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import OwnerId, SourceIdentifier


def _serialize_identifier(identifier: SourceIdentifier) -> str:
    """Sérialise un identifier pour la persistance."""
    return identifier.serialize()


class MongoDocumentRepository:
    """MongoDB implementation of DocumentRepository (delete-then-insert upsert)."""

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = "documents",
    ) -> None:
        self._database = client[db_name]
        self._collection = self._database[collection]

    @property
    def database(self) -> MongoDatabase:
        """La DB qui porte la collection — de quoi reposer les index après un drop."""
        return self._database

    async def upsert(self, document: ParsedDocument) -> None:
        """Delete existing entry then insert the new document."""
        identifier_key = _serialize_identifier(document.identifier)
        filter_ = {
            "identifier": identifier_key,
            "owner_id": document.owner_id,
        }
        await self._collection.delete_many(filter_)
        data = document.model_dump(mode="json")
        # Ajouter le champ sérialisé pour l'indexation
        data["identifier"] = identifier_key
        await self._collection.insert_one(data)

    async def delete(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None:
        await self._collection.delete_many(
            {
                "identifier": _serialize_identifier(identifier),
                "owner_id": owner_id,
            }
        )

    async def drop_collection(self) -> None:
        """Drop the entire collection. Irreversible — wipes all owners."""
        await self._collection.drop()
