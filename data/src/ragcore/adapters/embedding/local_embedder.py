"""Embedder local — sentence-transformers, sans réseau.

``sentence-transformers`` est un import PARESSEUX : il tire torch, soit plusieurs
centaines de mégaoctets. L'importer au niveau module imposerait ce coût à quiconque
importe ``ragcore.adapters.embedding`` — y compris les tests qui tournent en mode
``noop`` et n'en ont aucun besoin.
"""

from typing import TYPE_CHECKING

from ragcore.core.models.chunk import Chunk, EmbeddedChunk

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

__all__ = ["LocalEmbedder"]


class LocalEmbedder:
    """Implémentation de ``BaseEmbedder`` via un modèle chargé en mémoire."""

    def __init__(self, model_name: str, dimension: int) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._model: SentenceTransformer | None = None

    def _load(self) -> "SentenceTransformer":
        if self._model is None:
            # noqa: PLC0415 — l'import est paresseux DÉLIBÉRÉMENT : sentence-transformers
            # tire torch. Le hisser en tête imposerait ce coût à tout import de
            # `adapters.embedding`, y compris en mode noop qui n'en a aucun besoin.
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            self._model = SentenceTransformer(self._model_name)
            actual = self._model.get_sentence_embedding_dimension()
            if actual != self._dimension:
                # Qdrant refuserait le vecteur, mais bien plus loin et sous une
                # forme illisible. Le dire ici, c'est nommer la vraie cause.
                raise ValueError(
                    f"Le modèle '{self._model_name}' produit des vecteurs de "
                    f"dimension {actual}, or la configuration en déclare "
                    f"{self._dimension}. La collection Qdrant est créée à la "
                    f"dimension déclarée : les deux doivent coïncider."
                )
        return self._model

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []

        model = self._load()
        vectors = model.encode([chunk.text for chunk in chunks])

        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=[float(x) for x in vector],
                embedding_model=self._model_name,
                embedding_dim=self._dimension,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
