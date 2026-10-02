"""Implémentation MongoDB du DocumentRepository."""

from ragcore.adapters.storage.mongo.client import MongoClient, MongoDatabase
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import Identifier

_STRUCTURE_FIELD = "structure"
_SOURCE_FILES_FIELD = "source_files"


def _serialize_identifier(identifier: Identifier) -> str:
    return identifier.serialize()


def _excluded_fields(include_path: bool) -> set[str]:
    """``source_files`` n'est retiré que sans ``include_path``."""
    if include_path:
        return {_STRUCTURE_FIELD}
    return {_STRUCTURE_FIELD, _SOURCE_FILES_FIELD}


class MongoDocumentRepository:
    """``include_path`` écrit les chemins des fichiers source : une commodité de dev,
    ``False`` par défaut comme en prod.
    """

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = "documents",
        *,
        include_path: bool = False,
    ) -> None:
        self._database = client[db_name]
        self._collection = self._database[collection]
        self._excluded_fields = _excluded_fields(include_path)

    @property
    def database(self) -> MongoDatabase:
        """Celle que le nuke remet à neuf."""
        return self._database

    async def upsert(self, document: ParsedDocument) -> None:
        """Remplacement atomique : l'identifiant n'est jamais absent, la saga n'a rien à
        détruire avant d'écrire."""
        identifier_key = _serialize_identifier(document.identifier)
        filter_ = {"identifier": identifier_key}
        # `structure` n'est jamais écrit (ADR-011) : ses liens vivent dans Neo4j, ses
        # sections répètent `content`. Le chunker et l'extracteur le lisent en mémoire.
        data = document.model_dump(mode="json", exclude=self._excluded_fields)
        data["identifier"] = identifier_key
        await self._collection.replace_one(filter_, data, upsert=True)

    async def delete(self, identifier: Identifier) -> None:
        await self._collection.delete_many(
            {"identifier": _serialize_identifier(identifier)}
        )
