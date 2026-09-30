"""Le garde-fou du modèle servi, et le footgun qu'il ferme.

TEI ne sert qu'UN modèle et **ignore** le champ ``model`` de la requête. Le seul moyen de
savoir ce qu'il sert vraiment est de le lui demander (``GET /info``). Sans cette
vérification, une divergence entre le conteneur et ``parameters.yml`` écrit les vecteurs
d'un modèle dans la collection nommée d'après un autre — sans lever, sans logguer.
"""

import json

import httpx
import pytest

from ragcore.adapters.embedding.openai_embedder import (
    EmbeddingTransport,
    OpenAIEmbedder,
)
from ragcore.adapters.embedding.served_model import assert_service_serves_model
from ragcore.core.config import EmbeddingConfig
from ragcore.core.exceptions import EmbeddingModelMismatchError
from ragcore.core.models.chunk import Chunk
from ragcore.core.models.identifiers import Identifier, OwnerId

ATTENDU = "sentence-transformers/all-mpnet-base-v2"
BASE_URL = "http://tei.test:80/v1"
DIM = 4


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        parent_identifier=Identifier(raw="LEGIARTI000006419264"),
        owner_id=OwnerId("owner-1"),
        ordinal=0,
        text=text,
        tag_path=[],
        char_start=0,
        char_end=len(text),
        metadata={},
    )


class _ServiceFactice:
    """Un TEI en carton qui enregistre ce qu'on lui a demandé."""

    def __init__(
        self, *, model_id: str | None = ATTENDU, info_status: int = 200
    ) -> None:
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


async def test_un_service_qui_sert_un_autre_modele_fait_echouer_le_run(
    _patch_client,
) -> None:
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


async def test_info_est_interroge_a_l_ORIGINE_pas_sous_le_prefixe(
    _patch_client,
) -> None:
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
        OpenAIEmbedder(
            EmbeddingConfig(model_name=ATTENDU, dimension=768),
            EmbeddingTransport(base_url=None),
        )


async def test_embed_d_une_liste_vide_ne_touche_pas_au_reseau() -> None:
    embedder = OpenAIEmbedder(
        EmbeddingConfig(model_name=ATTENDU, dimension=768),
        EmbeddingTransport(base_url=BASE_URL),
    )
    assert await embedder.embed([]) == []


class _ServiceAFenetre:
    """Un TEI factice à fenêtre finie : il REJETTE (413) tout texte plus long que ``limite``.

    C'est exactement le mur que ``_embed_oversized`` doit franchir : le service ne dit pas
    QUEL texte déborde, seulement que le lot déborde. On peut donc rejouer la dichotomie
    réelle, sans mock partiel de l'embedder.
    """

    def __init__(self, limite: int) -> None:
        self._limite = limite

    def handler(self, request: httpx.Request) -> httpx.Response:
        textes = json.loads(request.content)["input"]
        if any(len(t) > self._limite for t in textes):
            return httpx.Response(413)
        data = [{"index": i, "embedding": [0.0] * DIM} for i in range(len(textes))]
        return httpx.Response(200, json={"data": data})

    def embedder(self) -> OpenAIEmbedder:
        emb = OpenAIEmbedder(
            EmbeddingConfig(model_name=ATTENDU, dimension=DIM),
            EmbeddingTransport(base_url=BASE_URL, batch_size=32),
        )
        # On câble le transport factice dans le client que l'embedder construira.
        vrai = httpx.AsyncClient

        def _fabrique(*a: object, **k: object) -> httpx.AsyncClient:
            k["transport"] = httpx.MockTransport(self.handler)
            return vrai(*a, **k)  # type: ignore[arg-type]

        emb._client = lambda: _fabrique()  # type: ignore[method-assign]
        return emb


class TestLeCompteurDeTruncations:
    async def test_un_chunk_raccourci_TROIS_fois_compte_UN(self) -> None:
        """Le cœur de F14 : on compte le CHUNK, pas les moitiés successives.

        Le texte fait 8 caractères, la fenêtre 1 : la dichotomie va le raccourcir
        8→4→2→1, soit trois raccourcissements du MÊME chunk. L'ancien compteur en
        aurait dit 3. Il ne doit en dire qu'un.
        """
        service = _ServiceAFenetre(limite=1)
        embedder = service.embedder()

        await embedder.embed([_chunk("c-unique", "textelong")])

        assert embedder.truncations == 1

    async def test_deux_chunks_debordent_le_compte_est_DEUX(self) -> None:
        """Deux chunks distincts, chacun trop long : deux truncations, pas plus."""
        service = _ServiceAFenetre(limite=2)
        embedder = service.embedder()

        await embedder.embed(
            [
                _chunk("c-1", "beaucoup trop long"),
                _chunk("c-2", "long aussi celui la"),
                _chunk("c-3", "ok"),  # tient dans la fenêtre : pas raccourci
            ]
        )

        assert embedder.truncations == 2

    async def test_aucun_debordement_ne_compte_rien(self) -> None:
        service = _ServiceAFenetre(limite=100)
        embedder = service.embedder()

        await embedder.embed([_chunk("c-1", "court"), _chunk("c-2", "bref")])

        assert embedder.truncations == 0
