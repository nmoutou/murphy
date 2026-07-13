"""Embedder distant — API compatible OpenAI (le service TEI du docker-compose).

Par lots : un corpus de dix mille chunks en dix mille requêtes HTTP serait lent
sans raison, et ferait tomber le service bien avant d'être lent.
"""

from urllib.parse import urlsplit, urlunsplit

import httpx

from ragcore.core.exceptions import EmbeddingModelMismatchError
from ragcore.core.models.chunk import Chunk, EmbeddedChunk

__all__ = ["OpenAIEmbedder", "assert_service_serves_model"]

_TIMEOUT_SECONDS = 120.0
_INFO_TIMEOUT_SECONDS = 10.0


async def assert_service_serves_model(base_url: str, expected_model: str) -> None:
    """Le service sert-il bien le modèle dont le nom **baptise la collection** (§6) ?

    TEI ignore le champ ``model`` de la requête : il ne sert que le modèle de son
    ``--model-id``. Une divergence entre le conteneur et ``parameters.yml`` écrit donc les
    vecteurs d'un modèle dans la collection nommée d'après un autre, **sans rien lever**.
    ``GET /info`` est le seul endroit où le service *dit* ce qu'il sert : c'est la seule
    façon de fermer le trou.

    Appelée **avant le pool** (depuis le hook), jamais depuis un worker — voir
    ``EmbeddingModelMismatchError``. Un service injoignable est **fatal** lui aussi : tant
    qu'on ne peut pas vérifier ce qu'il sert, on n'écrit pas.

    Miroir exact du garde-fou de dimension de ``_embed_batch`` : même esprit, même moment
    (avant d'écrire), même verdict (on refuse d'écrire).
    """
    # `/info` est à la RACINE du service, pas sous le préfixe `/v1` de l'API compatible
    # OpenAI. Interroger `{base_url}/info` donnerait un 404 — donc un garde-fou qui ne se
    # déclencherait jamais, ce qui est pire que pas de garde-fou du tout.
    parts = urlsplit(base_url)
    info_url = urlunsplit((parts.scheme, parts.netloc, "/info", "", ""))

    try:
        async with httpx.AsyncClient(timeout=_INFO_TIMEOUT_SECONDS) as client:
            response = await client.get(info_url)
            response.raise_for_status()
            served = response.json().get("model_id")
    except (httpx.HTTPError, ValueError) as exc:
        raise EmbeddingModelMismatchError(
            f"Impossible d'interroger {info_url} : {exc}. Le service d'embedding "
            f"est-il démarré (`npm run up`) ? Tant qu'on ne peut pas VÉRIFIER quel "
            f"modèle il sert, on n'écrit pas."
        ) from exc

    if served != expected_model:
        raise EmbeddingModelMismatchError(
            f"Le service sert « {served} », or la configuration déclare "
            f"« {expected_model} ». TEI ignore le champ `model` de la requête : il ne "
            f"sert QUE le modèle de son `--model-id`. Continuer écrirait les vecteurs de "
            f"« {served} » dans la collection nommée d'après l'empreinte de "
            f"« {expected_model} », sans que rien ne le signale. Aligner EMBEDDING_MODEL "
            f"(.env.dev, à la racine) et embedding.embedding.embedding_model "
            f"(conf/base/parameters.yml)."
        )


class OpenAIEmbedder:
    """Implémentation de ``BaseEmbedder`` via ``POST /embeddings``."""

    def __init__(
        self,
        model_name: str,
        dimension: int,
        api_key: str | None = None,
        batch_size: int = 32,
        base_url: str | None = None,
    ) -> None:
        if not base_url:
            # L'ancien défaut retombait sur `https://api.openai.com/v1` : un
            # EMBEDDING_SERVICE_URL oublié envoyait SILENCIEUSEMENT tout le corpus chez
            # OpenAI — facturé, et avec un autre modèle que celui dont le nom baptise la
            # collection. Un défaut ne doit jamais désigner un service tiers payant.
            raise ValueError(
                "OpenAIEmbedder exige une `base_url` explicite. Renseigner "
                "EMBEDDING_SERVICE_URL (p. ex. http://localhost:5001/v1)."
            )
        self._model_name = model_name
        self._dimension = dimension
        self._api_key = api_key
        self._batch_size = batch_size
        self._base_url = base_url.rstrip("/")

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if not chunks:
            return []

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        embedded: list[EmbeddedChunk] = []
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            for start in range(0, len(chunks), self._batch_size):
                batch = chunks[start : start + self._batch_size]
                vectors = await self._embed_batch(client, headers, batch)
                embedded.extend(
                    EmbeddedChunk(
                        chunk=chunk,
                        embedding=vector,
                        embedding_model=self._model_name,
                        embedding_dim=self._dimension,
                    )
                    for chunk, vector in zip(batch, vectors, strict=True)
                )
        return embedded

    async def _embed_batch(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        batch: list[Chunk],
    ) -> list[list[float]]:
        response = await client.post(
            f"{self._base_url}/embeddings",
            headers=headers,
            json={"model": self._model_name, "input": [c.text for c in batch]},
        )
        response.raise_for_status()

        # L'API ne garantit pas l'ordre : elle garantit l'index. Se fier à l'ordre
        # d'arrivée associerait le vecteur d'un chunk au texte d'un autre — une
        # corruption qui ne lève rien et ne se voit qu'à la recherche.
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
