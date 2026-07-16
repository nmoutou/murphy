from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.identifiers import OwnerId, SourceIdentifier


@runtime_checkable
class DocumentRepository(Protocol):
    """Stockage des documents parsés (MongoDB)."""

    async def upsert(self, document: ParsedDocument) -> None: ...

    async def delete(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None: ...
