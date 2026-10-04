from typing import Protocol, runtime_checkable

from ..models.chunk import Chunk, EmbeddedChunk


@runtime_checkable
class BaseEmbedder(Protocol):
    """Vectorisation des fragments, par lots auprès du service d'embedding."""

    @property
    def dimension(self) -> int:
        """Celle des champs vectoriels de l'index."""
        ...

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...

    async def embed_text(self, text: str) -> list[float]:
        """Un texte hors chunk : le titre d'un document sans passage."""
        ...
