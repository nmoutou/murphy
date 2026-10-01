"""L'embedder TEI, et la précondition du run : le modèle servi et sa dimension. TEI
ignore le champ ``model`` : seul ``GET /info`` dit ce qu'il sert.
"""

import json

import httpx
import pytest

from ragcore.adapters.embedding.served_model import inspect_served_model
from ragcore.adapters.embedding.tei_embedder import EmbeddingTransport, TeiEmbedder
from ragcore.core.exceptions import EmbeddingModelMismatchError
from ragcore.core.models.chunk import Chunk
from ragcore.core.models.enums import DocumentType
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.processing import EmbeddingModel

ATTENDU = "sentence-transformers/all-mpnet-base-v2"
BASE_URL = "http://tei.test:80/v1"
DIM = 4
TIMEOUT_MS = 2500
SERVED_DIMENSION = 768


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        parent_identifier=Identifier(raw="LEGIARTI000006419264"),
        document_type=DocumentType.ARTICLE,
        ordinal=0,
        text=text,
        tag_path=[],
        char_start=0,
        char_end=len(text),
        metadata={},
    )


class _ServiceFactice:
    """Un faux TEI qui enregistre les requêtes reçues."""

    def __init__(
        self,
        *,
        model_id: str | None = ATTENDU,
        info_status: int = 200,
        probe_status: int = 200,
    ) -> None:
        self._model_id = model_id
        self._info_status = info_status
        self._probe_status = probe_status
        self.chemins: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.chemins.append(request.url.path)
        if request.url.path == "/info":
            if self._info_status != 200:
                return httpx.Response(self._info_status)
            return httpx.Response(200, json={"model_id": self._model_id})
        if request.url.path == "/v1/embeddings":
            if self._probe_status != 200:
                return httpx.Response(self._probe_status)
            vector = [0.0] * SERVED_DIMENSION
            return httpx.Response(
                200, json={"data": [{"index": 0, "embedding": vector}]}
            )
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
    """Le run s'arrête plutôt que d'écrire les vecteurs d'un autre modèle."""
    service = _ServiceFactice(model_id="thenlper/gte-base")
    _patch_client(service)

    with pytest.raises(EmbeddingModelMismatchError) as erreur:
        await inspect_served_model(BASE_URL, ATTENDU)

    # L'erreur nomme les deux modèles
    assert "gte-base" in str(erreur.value)
    assert ATTENDU in str(erreur.value)


async def test_le_bon_modele_passe_et_sa_dimension_est_mesuree(_patch_client) -> None:
    _patch_client(_ServiceFactice(model_id=ATTENDU))

    model = await inspect_served_model(BASE_URL, ATTENDU)

    assert model == EmbeddingModel(model_name=ATTENDU, dimension=SERVED_DIMENSION)


async def test_info_est_interroge_a_l_ORIGINE_et_la_sonde_sous_le_prefixe(
    _patch_client,
) -> None:
    """`/info` est à la racine du service, `/embeddings` sous `/v1` : un 404 sur
    `/info` désarmerait le garde-fou."""
    service = _ServiceFactice()
    _patch_client(service)

    await inspect_served_model(BASE_URL, ATTENDU)

    assert service.chemins == ["/info", "/v1/embeddings"]


async def test_un_service_injoignable_ne_passe_pas_en_silence(_patch_client) -> None:
    """Tant qu'on ne peut pas vérifier ce qu'il sert, on n'écrit pas."""
    _patch_client(_ServiceFactice(info_status=503))

    with pytest.raises(EmbeddingModelMismatchError):
        await inspect_served_model(BASE_URL, ATTENDU)


async def test_une_sonde_en_echec_arrete_le_run(_patch_client) -> None:
    """Sans dimension, la collection Qdrant ne peut pas être créée."""
    _patch_client(_ServiceFactice(probe_status=500))

    with pytest.raises(EmbeddingModelMismatchError, match="sonde"):
        await inspect_served_model(BASE_URL, ATTENDU)


async def test_embed_d_une_liste_vide_ne_touche_pas_au_reseau() -> None:
    embedder = TeiEmbedder(
        EmbeddingModel(model_name=ATTENDU, dimension=768),
        EmbeddingTransport(base_url=BASE_URL, timeout_ms=TIMEOUT_MS),
    )
    assert await embedder.embed([]) == []


async def test_le_timeout_du_transport_s_applique_au_client_http() -> None:
    embedder = TeiEmbedder(
        EmbeddingModel(model_name=ATTENDU, dimension=768),
        EmbeddingTransport(base_url=BASE_URL, timeout_ms=TIMEOUT_MS),
    )

    assert embedder._client().timeout.read == TIMEOUT_MS / 1000


class _ServiceAFenetre:
    """Un faux TEI à fenêtre finie : 413 au-delà de ``limite``, sans dire quel texte
    déborde. De quoi rejouer la vraie dichotomie."""

    def __init__(self, limite: int) -> None:
        self._limite = limite

    def handler(self, request: httpx.Request) -> httpx.Response:
        textes = json.loads(request.content)["input"]
        if any(len(t) > self._limite for t in textes):
            return httpx.Response(413)
        data = [{"index": i, "embedding": [0.0] * DIM} for i in range(len(textes))]
        return httpx.Response(200, json={"data": data})

    def embedder(self) -> TeiEmbedder:
        emb = TeiEmbedder(
            EmbeddingModel(model_name=ATTENDU, dimension=DIM),
            EmbeddingTransport(base_url=BASE_URL, timeout_ms=TIMEOUT_MS, batch_size=32),
        )
        # Le faux transport, dans le client que l'embedder construira
        vrai = httpx.AsyncClient

        def _fabrique(*a: object, **k: object) -> httpx.AsyncClient:
            k["transport"] = httpx.MockTransport(self.handler)
            return vrai(*a, **k)  # type: ignore[arg-type]

        emb._client = lambda: _fabrique()  # type: ignore[method-assign]
        return emb


class TestLeCompteurDeTruncations:
    async def test_un_chunk_raccourci_TROIS_fois_compte_UN(self) -> None:
        """Un chunk raccourci trois fois (8→4→2→1) compte une fois."""
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
