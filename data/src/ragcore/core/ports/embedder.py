from typing import Protocol, runtime_checkable

from ..models.chunk import Chunk, EmbeddedChunk


@runtime_checkable
class BaseEmbedder(Protocol):
    """Vectorisation des fragments.

    Le seul port de traitement qui soit asynchrone : l'implémentation appelle
    un service distant ou un modèle local, par lots.
    """

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]: ...
