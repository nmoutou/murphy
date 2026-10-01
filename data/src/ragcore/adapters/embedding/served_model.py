"""La précondition du run : TEI sert-il le modèle attendu, et à quelle dimension ?"""

from urllib.parse import urlsplit, urlunsplit

import httpx

from ragcore.core.exceptions import EmbeddingModelMismatchError
from ragcore.core.models.processing import EmbeddingModel

__all__ = ["inspect_served_model"]

_INSPECTION_TIMEOUT_SECONDS = 10.0

_PROBE_TEXT = "sonde de dimension"
"""Seule compte la taille du vecteur obtenu."""


async def inspect_served_model(base_url: str, expected_model: str) -> EmbeddingModel:
    """Le modèle que sert TEI, vérifié contre ``EMBEDDING_MODEL``, et sa dimension mesurée.

    TEI ignore le champ ``model`` de la requête : seul ``GET /info`` dit ce qu'il sert.
    La dimension n'est pas déclarée, une requête de sonde la mesure.

    À appeler avant le pool, jamais depuis un worker (cf.
    ``EmbeddingModelMismatchError``). Un service injoignable est fatal aussi.
    """
    async with httpx.AsyncClient(timeout=_INSPECTION_TIMEOUT_SECONDS) as client:
        served = await _served_model_id(client, base_url)
        if served != expected_model:
            raise EmbeddingModelMismatchError(
                f"Le service sert « {served} », or EMBEDDING_MODEL vaut "
                f"« {expected_model} ». TEI ignore le champ `model` de la requête : il ne "
                f"sert QUE le modèle de son `--model-id`. Continuer écrirait les vecteurs "
                f"de « {served} » dans une collection que le backend interroge avec "
                f"« {expected_model} ». Redémarrer TEI après avoir changé EMBEDDING_MODEL "
                f"(.env.dev, à la racine) : `npm run ingest:up`."
            )
        dimension = await _probe_dimension(client, base_url, expected_model)
    return EmbeddingModel(model_name=expected_model, dimension=dimension)


async def _served_model_id(client: httpx.AsyncClient, base_url: str) -> object:
    # `/info` est à la racine du service, pas sous le préfixe `/v1` de `base_url`
    parts = urlsplit(base_url)
    info_url = urlunsplit((parts.scheme, parts.netloc, "/info", "", ""))
    try:
        response = await client.get(info_url)
        response.raise_for_status()
        return response.json().get("model_id")
    except (httpx.HTTPError, ValueError) as exc:
        raise EmbeddingModelMismatchError(
            f"Impossible d'interroger {info_url} : {exc}. Le service d'embedding "
            f"est-il démarré (`npm run ingest:up`) ? Tant qu'on ne peut pas VÉRIFIER quel "
            f"modèle il sert, on n'écrit pas."
        ) from exc


async def _probe_dimension(
    client: httpx.AsyncClient, base_url: str, model_name: str
) -> int:
    probe_url = f"{base_url.rstrip('/')}/embeddings"
    try:
        response = await client.post(
            probe_url, json={"model": model_name, "input": [_PROBE_TEXT]}
        )
        response.raise_for_status()
        return len(response.json()["data"][0]["embedding"])
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise EmbeddingModelMismatchError(
            f"La sonde de dimension a échoué ({probe_url}) : {exc!r}. Sans la dimension "
            f"des vecteurs, la collection Qdrant ne peut pas être créée : on n'écrit pas."
        ) from exc
