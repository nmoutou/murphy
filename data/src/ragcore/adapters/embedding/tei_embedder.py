"""L'embedder de l'ingestion : TEI, par son API compatible OpenAI, par lots."""

import asyncio
import logging
import threading
from dataclasses import dataclass

import httpx

from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.processing import EmbeddingModel

__all__ = ["EmbeddingTransport", "TeiEmbedder"]

_LOGGER = logging.getLogger(__name__)

_MS_PER_SECOND = 1000

# Lot hors fenêtre du modèle : pas une panne, c'est ainsi que le service dit la limite
_PAYLOAD_TOO_LARGE = 413


def _rejected(chunk: Chunk) -> ValueError:
    return ValueError(
        f"Le service refuse le chunk {chunk.chunk_id} même vide : le rejet n'est pas une "
        f"question de taille. Vérifier la santé du service d'embedding."
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
        # Des `chunk_id` plutôt qu'un compteur : la dichotomie raccourcit un même chunk
        # plusieurs fois. Verrouillé : l'embedder est partagé entre les threads workers.
        self._truncated_chunk_ids: set[str] = set()
        self._truncations_lock = threading.Lock()
        # Un client par boucle : un client httpx est lié à la boucle qui l'a créé, et
        # l'embedder est partagé entre les workers.
        self._clients: dict[object, httpx.AsyncClient] = {}

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def truncations(self) -> int:
        """Combien de chunks distincts ont été raccourcis, pas combien de fois."""
        with self._truncations_lock:
            return len(self._truncated_chunk_ids)

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
        if not chunks:
            return []

        headers = {"Content-Type": "application/json"}

        client = self._client()
        batches = [
            chunks[start : start + self._batch_size]
            for start in range(0, len(chunks), self._batch_size)
        ]

        # En parallèle : une requête TEI coûte ~800 ms de frais fixes, et TEI regroupe
        # les requêtes en vol côté GPU. `gather` préserve l'ordre des vecteurs.
        results = await asyncio.gather(
            *(self._embed_batch(client, headers, batch) for batch in batches)
        )

        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self._model_name,
                embedding_dim=self._dimension,
            )
            for batch, vectors in zip(batches, results, strict=True)
            for chunk, vector in zip(batch, vectors, strict=True)
        ]

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        batch: list[Chunk],
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
            json={"model": self._model_name, "input": [c.text for c in batch]},
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
                    f"or la configuration en déclare {self._dimension}. La collection "
                    f"Qdrant est créée à la dimension déclarée : les deux doivent "
                    f"coïncider."
                )
        return vectors

    async def _embed_oversized(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        batch: list[Chunk],
    ) -> list[list[float]]:
        """Le 413 ne dit pas quel chunk déborde : la dichotomie isole le fautif en
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
        chunk = batch[0]
        if not chunk.text:
            # Refusé même vide : pas une question de taille
            raise _rejected(chunk)

        shrunk = chunk.model_copy(update={"text": chunk.text[: len(chunk.text) // 2]})
        with self._truncations_lock:
            self._truncated_chunk_ids.add(str(chunk.chunk_id))
        _LOGGER.warning(
            "chunk hors fenêtre du modèle — raccourci de %d à %d caractères (chunk_id=%s). "
            "Le document est sauvé, mais la fin de ce chunk n'est pas indexée : le vrai "
            "correctif est un `CHUNKING_MAX_CHARS` compatible avec la fenêtre.",
            len(chunk.text),
            len(shrunk.text),
            chunk.chunk_id,
        )
        return await self._embed_batch(client, headers, [shrunk])
