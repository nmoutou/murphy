"""L'embedder de l'ingestion : TEI, par son API compatible OpenAI, par lots."""

import asyncio
import logging
import threading
from dataclasses import dataclass, replace

import httpx

from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.processing import EmbeddingModel

__all__ = ["EmbeddingTransport", "TeiEmbedder"]

_LOGGER = logging.getLogger(__name__)

_MS_PER_SECOND = 1000

# Lot hors fenêtre du modèle : pas une panne, c'est ainsi que le service dit la limite
_PAYLOAD_TOO_LARGE = 413


@dataclass(frozen=True)
class _EmbeddingInput:
    key: str
    """Nomme le texte dans les logs et le compte des raccourcis : un ``chunk_id``, ou
    le texte lui-même hors chunk."""
    text: str


def _rejected(embedding_input: _EmbeddingInput) -> ValueError:
    return ValueError(
        f"Le service refuse le texte {embedding_input.key} même vide : le rejet n'est "
        f"pas une question de taille. Vérifier la santé du service d'embedding."
    )


@dataclass(frozen=True)
class EmbeddingTransport:
    base_url: str
    timeout_ms: int
    """Par requête (``EMBEDDING_INGESTION_TIMEOUT``)."""
    batch_size: int = 32


class TeiEmbedder:
    def __init__(self, model: EmbeddingModel, transport: EmbeddingTransport) -> None:
        self._model_name = model.model_name
        self._dimension = model.dimension
        self._batch_size = transport.batch_size
        self._timeout_seconds = transport.timeout_ms / _MS_PER_SECOND
        self._base_url = transport.base_url.rstrip("/")
        # Des clés plutôt qu'un compteur : la dichotomie raccourcit un même chunk
        # plusieurs fois. Verrouillé : l'embedder est partagé entre les threads workers.
        self._truncated_keys: set[str] = set()
        self._truncations_lock = threading.Lock()
        # Un client par boucle : un client httpx est lié à la boucle qui l'a créé, et
        # l'embedder est partagé entre les workers.
        self._clients: dict[object, httpx.AsyncClient] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def truncations(self) -> int:
        """Combien de textes distincts ont été raccourcis, pas combien de fois."""
        with self._truncations_lock:
            return len(self._truncated_keys)

    def _client(self) -> httpx.AsyncClient:
        # Jamais fermé explicitement : `aclose()` ne peut tourner que dans la boucle du
        # worker, que le hook ne voit pas. Le socket part avec la boucle, en fin de run.
        loop = asyncio.get_running_loop()
        client = self._clients.get(loop)
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout_seconds)
            self._clients[loop] = client
        return client

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        vectors = await self._embed_all(
            [_EmbeddingInput(key=chunk.chunk_id, text=chunk.text) for chunk in chunks]
        )
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self._model_name,
                embedding_dim=self._dimension,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]

    async def embed_text(self, text: str) -> list[float]:
        [vector] = await self._embed_all([_EmbeddingInput(key=text, text=text)])
        return vector

    async def _embed_all(self, inputs: list[_EmbeddingInput]) -> list[list[float]]:
        if not inputs:
            return []

        headers = {"Content-Type": "application/json"}

        client = self._client()
        batches = [
            inputs[start : start + self._batch_size]
            for start in range(0, len(inputs), self._batch_size)
        ]

        # En parallèle : une requête TEI coûte ~800 ms de frais fixes, et TEI regroupe
        # les requêtes en vol côté GPU. `gather` préserve l'ordre des vecteurs.
        results = await asyncio.gather(
            *(self._embed_batch(client, headers, batch) for batch in batches)
        )
        return [vector for vectors in results for vector in vectors]

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        batch: list[_EmbeddingInput],
    ) -> list[list[float]]:
        """Un chunk trop long est raccourci, jamais perdu.

        Le service rejette tout le lot si un seul chunk dépasse la fenêtre du modèle. Aucun
        ``CHUNKING_MAX_CHARS`` n'est sûr par construction : le chunker compte en
        caractères, le modèle en tokens, et le ratio va de 3,08 car/token en moyenne à
        0,33 au pire.
        """
        response = await client.post(
            f"{self._base_url}/embeddings",
            headers=headers,
            json={"model": self._model_name, "input": [entry.text for entry in batch]},
        )

        if response.status_code == _PAYLOAD_TOO_LARGE:
            return await self._embed_oversized(client, headers, batch)

        response.raise_for_status()

        # L'API garantit l'index, pas l'ordre
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        vectors = [item["embedding"] for item in data]

        for vector in vectors:
            if len(vector) != self._dimension:
                raise ValueError(
                    f"Le service a renvoyé des vecteurs de dimension {len(vector)}, "
                    f"or la sonde du démarrage en a mesuré {self._dimension}, celle du "
                    f"mapping de l'index : les deux doivent coïncider."
                )
        return vectors

    async def _embed_oversized(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        batch: list[_EmbeddingInput],
    ) -> list[list[float]]:
        """Le 413 ne dit pas quel texte déborde : la dichotomie isole le fautif en
        ``log(n)`` requêtes, et lui seul est tronqué."""
        if len(batch) > 1:
            middle = len(batch) // 2
            left, right = await asyncio.gather(
                self._embed_batch(client, headers, batch[:middle]),
                self._embed_batch(client, headers, batch[middle:]),
            )
            return [*left, *right]

        # Raccourci de moitié à chaque tour : la récursion termine, sans connaître la
        # fenêtre du modèle.
        oversized = batch[0]
        if not oversized.text:
            # Refusé même vide : pas une question de taille
            raise _rejected(oversized)

        shrunk = replace(oversized, text=oversized.text[: len(oversized.text) // 2])
        with self._truncations_lock:
            self._truncated_keys.add(oversized.key)
        _LOGGER.warning(
            "texte hors fenêtre du modèle — raccourci de %d à %d caractères (%s). "
            "Le document est sauvé, mais la fin de ce texte n'est pas indexée : le vrai "
            "correctif est un `CHUNKING_MAX_CHARS` compatible avec la fenêtre.",
            len(oversized.text),
            len(shrunk.text),
            oversized.key,
        )
        return await self._embed_batch(client, headers, [shrunk])
