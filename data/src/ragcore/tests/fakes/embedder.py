"""Un embedder sans service : des vecteurs nuls, de la bonne dimension.

Il rend testable ce qui n'est PAS la vectorisation (la saga, le bilan de run) sans
TEI. Il ment sur le contenu, jamais sur la forme : Qdrant rejette un vecteur d'une
autre taille que sa collection.
"""

from ragcore.core.models.chunk import Chunk, EmbeddedChunk

__all__ = ["NoopEmbedder"]

_MODEL_NAME = "noop"


class NoopEmbedder:
    """Implémentation de ``BaseEmbedder`` produisant des vecteurs nuls."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        zero = [0.0] * self._dimension
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=list(zero),
                embedding_model=_MODEL_NAME,
                embedding_dim=self._dimension,
            )
            for chunk in chunks
        ]
