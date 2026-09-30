from typing import Protocol, runtime_checkable

from ..models.chunk import Chunk, EmbeddedChunk


@runtime_checkable
class BaseEmbedder(Protocol):
    """Vectorisation des fragments.

    Le seul port de traitement qui soit asynchrone : l'implémentation appelle le service
    d'embedding, par lots.
    """

    @property
    def dimension(self) -> int:
        """La taille des vecteurs produits : celle de la collection Qdrant."""
        ...

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...
