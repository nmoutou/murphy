"""Le garde-fou du modèle servi, et le footgun qu'il ferme.

TEI ne sert qu'UN modèle et **ignore** le champ ``model`` de la requête. Le seul moyen de
savoir ce qu'il sert vraiment est de le lui demander (``GET /info``). Sans cette
vérification, une divergence entre le conteneur et ``parameters.yml`` écrit les vecteurs
d'un modèle dans la collection nommée d'après un autre — sans lever, sans logguer.
"""

import httpx
import pytest

from ragcore.adapters.embedding.openai_embedder import (
    OpenAIEmbedder,
    assert_service_serves_model,
)
from ragcore.core.exceptions import EmbeddingModelMismatchError

ATTENDU = "sentence-transformers/all-mpnet-base-v2"
BASE_URL = "http://tei.test:80/v1"


class _ServiceFactice:
    """Un TEI en carton qui enregistre ce qu'on lui a demandé."""

    def __init__(self, *, model_id: str | None = ATTENDU, info_status: int = 200) -> None:
        self._model_id = model_id
        self._info_status = info_status
        self.chemins: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.chemins.append(request.url.path)
        if request.url.path == "/info":
            if self._info_status != 200:
                return httpx.Response(self._info_status)
            return httpx.Response(200, json={"model_id": self._model_id})
        return httpx.Response(404)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


@pytest.fixture
def _patch_client(monkeypatch: pytest.MonkeyPatch):
    """Câble le transport factice dans l'``AsyncClient`` que le helper construit lui-même."""

    def _installe(service: _ServiceFactice) -> None:
        vrai_client = httpx.AsyncClient

        def _fabrique(*args: object, **kwargs: object) -> httpx.AsyncClient:
            kwargs["transport"] = service.transport()
            return vrai_client(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(httpx, "AsyncClient", _fabrique)

    return _installe


async def test_un_service_qui_sert_un_autre_modele_fait_echouer_le_run(_patch_client) -> None:
    """LE test qui justifie la feature : le run doit s'arrêter, pas produire des vecteurs.

    Sans lui, on écrit les vecteurs de `gte-base` dans la collection dont le nom est
    l'empreinte d'`all-mpnet-base-v2`. Deux jeux incomparables dans un même index.
    """
    service = _ServiceFactice(model_id="thenlper/gte-base")
    _patch_client(service)

    with pytest.raises(EmbeddingModelMismatchError) as erreur:
        await assert_service_serves_model(BASE_URL, ATTENDU)

    # L'erreur doit NOMMER les deux modèles : un message qui dit « ça ne colle pas »
    # sans dire quoi force à aller lire le code.
    assert "gte-base" in str(erreur.value)
    assert ATTENDU in str(erreur.value)


async def test_le_bon_modele_passe(_patch_client) -> None:
    service = _ServiceFactice(model_id=ATTENDU)
    _patch_client(service)

    await assert_service_serves_model(BASE_URL, ATTENDU)  # ne lève pas


async def test_info_est_interroge_a_l_ORIGINE_pas_sous_le_prefixe(_patch_client) -> None:
    """`/info` est à la racine du service, pas sous `/v1`.

    S'y tromper donne un 404 — donc un garde-fou qui ne se déclenche JAMAIS, ce qui est
    pire que pas de garde-fou : on croit être protégé.
    """
    service = _ServiceFactice()
    _patch_client(service)

    await assert_service_serves_model(BASE_URL, ATTENDU)

    assert service.chemins == ["/info"]
    assert "/v1/info" not in service.chemins


async def test_un_service_injoignable_ne_passe_pas_en_silence(_patch_client) -> None:
    """Tant qu'on ne peut pas VÉRIFIER ce qu'il sert, on n'écrit pas."""
    service = _ServiceFactice(info_status=503)
    _patch_client(service)

    with pytest.raises(EmbeddingModelMismatchError):
        await assert_service_serves_model(BASE_URL, ATTENDU)


def test_une_base_url_absente_est_refusee() -> None:
    """Le défaut retombait sur `https://api.openai.com/v1` : un EMBEDDING_SERVICE_URL
    oublié envoyait tout le corpus chez OpenAI, facturé, avec un autre modèle."""
    with pytest.raises(ValueError, match="base_url"):
        OpenAIEmbedder(model_name=ATTENDU, dimension=768, base_url=None)


async def test_embed_d_une_liste_vide_ne_touche_pas_au_reseau() -> None:
    embedder = OpenAIEmbedder(model_name=ATTENDU, dimension=768, base_url=BASE_URL)
    assert await embedder.embed([]) == []
