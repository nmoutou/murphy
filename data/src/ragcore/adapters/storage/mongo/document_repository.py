"""Implémentation MongoDB du DocumentRepository."""

from motor.motor_asyncio import AsyncIOMotorClient

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import OwnerId, SourceIdentifier


def _serialize_identifier(identifier: SourceIdentifier) -> str:
    """Sérialise un identifier pour la persistance."""
    return identifier.serialize()


class MongoDocumentRepository:
    """MongoDB implementation of DocumentRepository (delete-then-insert upsert)."""

    def __init__(
        self,
        client: AsyncIOMotorClient,
        db_name: str,
        collection: str = "documents",
    ) -> None:
        self._collection = client[db_name][collection]

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

    async def get(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> ParsedDocument | None:
        doc = await self._collection.find_one(
            {
                "identifier": _serialize_identifier(identifier),
                "owner_id": owner_id,
            }
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        # Le champ "identifier" sérialisé n'est pas dans le modèle ParsedDocument
        # Il sera reconstruit à partir du champ source-spécifique
        doc.pop("identifier", None)
        return ParsedDocument.model_validate(doc)

    async def exists(self, identifier: SourceIdentifier, owner_id: OwnerId) -> bool:
        count = await self._collection.count_documents(
            {
                "identifier": _serialize_identifier(identifier),
                "owner_id": owner_id,
            },
            limit=1,
        )
        return count > 0

    async def drop_collection(self) -> None:
        """Drop the entire collection. Irreversible — wipes all owners."""
        await self._collection.drop()
