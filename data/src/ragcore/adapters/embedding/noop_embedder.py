"""L'embedder qui n'embarque rien — et ce n'est pas un bouchon.

C'est le seul mode où le pipeline tourne sans GPU, sans modèle téléchargé et sans
réseau. Il rend testable de bout en bout tout ce qui n'est PAS la vectorisation :
la saga, la barrière bi-phasée, l'idempotence, le bilan de run. Un pipeline qu'on
ne peut exécuter qu'avec une carte graphique est un pipeline qu'on n'exécute pas.

Les vecteurs sont nuls, et la recherche sémantique construite dessus n'a aucun
sens — c'est assumé. Ce que cet embedder promet, c'est la BONNE DIMENSION : Qdrant
crée sa collection à cette taille, et un vecteur de taille différente serait
rejeté. Il ment sur le contenu, jamais sur la forme.
"""

from ragcore.core.models.chunk import Chunk, EmbeddedChunk

__all__ = ["NoopEmbedder"]

_MODEL_NAME = "noop"


class NoopEmbedder:
    """Implémentation de ``BaseEmbedder`` produisant des vecteurs nuls."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

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
