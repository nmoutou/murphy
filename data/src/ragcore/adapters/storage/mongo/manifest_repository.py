"""Implémentation MongoDB du ManifestRepository — append-only avec deux modes d'indexation."""

from motor.motor_asyncio import AsyncIOMotorClient

from ragcore.core.models.identifiers import OwnerId, SourceIdentifier
from ragcore.core.models.manifest import ManifestEntry


class MongoManifestRepository:
    """MongoDB implementation of ManifestRepository (append-only, dual-indexed).
    
    Deux modes d'indexation coexistent :
    - Index sur (identifier_serialized, owner_id) pour l'idempotence (valides)
    - Index sur (source_path, owner_id) pour l'audit des rejets
    """

    def __init__(
        self,
        client: AsyncIOMotorClient,
        db_name: str,
        collection: str = "manifest",
    ) -> None:
        self._collection = client[db_name][collection]

    async def append(self, entry: ManifestEntry) -> None:
        """Ajoute une nouvelle entrée (insert, pas d'upsert)."""
        data = entry.model_dump(mode="json")
        # Sérialiser l'identifier pour l'indexation MongoDB
        if entry.identifier is not None:
            data["identifier_serialized"] = entry.identifier.serialize()
        await self._collection.insert_one(data)

    async def last_for_identifier(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> ManifestEntry | None:
        """Récupère la dernière entrée pour cet identifier (tri par processed_at DESC)."""
        doc = await self._collection.find_one(
            {
                "identifier_serialized": identifier.serialize(),
                "owner_id": owner_id,
            },
            sort=[("processed_at", -1)],
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        doc.pop("identifier_serialized", None)  # Pas besoin après le fetch
        return ManifestEntry.model_validate(doc)

    async def last_for_source_path(
        self, source_path: str, owner_id: OwnerId
    ) -> ManifestEntry | None:
        """Récupère la dernière entrée pour ce chemin source (pour audit des rejets)."""
        doc = await self._collection.find_one(
            {"source_path": source_path, "owner_id": owner_id},
            sort=[("processed_at", -1)],
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        doc.pop("identifier_serialized", None)
        return ManifestEntry.model_validate(doc)

    async def delete(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None:
        """Supprime toutes les entrées pour cet identifier."""
        await self._collection.delete_many(
            {
                "identifier_serialized": identifier.serialize(),
                "owner_id": owner_id,
            }
        )

    async def drop_collection(self) -> None:
        """Drop the entire manifest collection. Irreversible — wipes all owners."""
        await self._collection.drop()
