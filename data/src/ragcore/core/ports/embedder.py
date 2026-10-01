from typing import Protocol, runtime_checkable

from ..models.chunk import Chunk, EmbeddedChunk


@runtime_checkable
class BaseEmbedder(Protocol):
    """Vectorisation des fragments, par lots auprès du service d'embedding."""

    @property
    def dimension(self) -> int:
        """Celle de la collection Qdrant."""
        ...

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...
