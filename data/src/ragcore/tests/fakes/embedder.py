"""Des vecteurs nuls, de la bonne dimension : faux sur le contenu, jamais sur la forme,
que Qdrant vérifie.
"""

from ragcore.core.models.chunk import Chunk, EmbeddedChunk

__all__ = ["NoopEmbedder"]

_MODEL_NAME = "noop"


class NoopEmbedder:
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
