from typing import Protocol, runtime_checkable

from ..models.chunk import EmbeddedChunk
from ..models.identifiers import OwnerId, SourceIdentifier


@runtime_checkable
class VectorRepository(Protocol):
    """Stockage vectoriel (Qdrant) — delete-then-insert."""

    async def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> None: ...

    async def delete_by_document(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None: ...
