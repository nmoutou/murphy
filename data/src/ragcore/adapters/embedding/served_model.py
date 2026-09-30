"""La précondition du run : le service d'embedding sert-il le modèle attendu ?"""

from urllib.parse import urlsplit, urlunsplit

import httpx

from ragcore.core.exceptions import EmbeddingModelMismatchError

__all__ = ["assert_service_serves_model"]

_INFO_TIMEOUT_SECONDS = 10.0


async def assert_service_serves_model(base_url: str, expected_model: str) -> None:
    """Le service sert-il bien le modèle que la configuration déclare ?

    TEI ignore le champ ``model`` de la requête : il ne sert que le modèle de son
    ``--model-id``. Une divergence entre le conteneur et ``parameters.yml`` écrit donc les
    vecteurs d'un autre modèle que celui que le backend interroge, **sans rien lever**.
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
            f"« {served} » dans une collection que le backend interroge avec "
            f"« {expected_model} », sans que rien ne le signale. Aligner EMBEDDING_MODEL "
            f"(.env.dev, à la racine) et embedding.model_name "
            f"(conf/base/parameters.yml)."
        )
