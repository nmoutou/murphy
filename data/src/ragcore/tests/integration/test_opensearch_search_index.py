"""L'index contre un vrai OpenSearch : le mapping strict, les analyseurs et le
remplacement d'un document ne se prouvent qu'avec le moteur.
"""

import pytest
from opensearchpy import RequestError
from testcontainers.opensearch import OpenSearchContainer

from ragcore.adapters.storage.opensearch.client import create_opensearch_client
from ragcore.adapters.storage.opensearch.search_index import OpenSearchSearchIndex
from ragcore.core.models.chunk import Chunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.search_content import IndexedPassage, SearchContent

pytestmark = pytest.mark.integration

INDEX = "documents_test"
OTHER_INDEX = "autre_index"
DIM = 768
IDENTIFIER = Identifier(raw="LEGIARTI000000000001")


def _doc(metadata: dict[str, str] | None = None) -> ParsedDocument:
    return ParsedDocument(
        identifier=IDENTIFIER,
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title="L52-8",
        content="x" * 100,
        structure={},
        metadata=metadata or {},
    )


def _content(passage_count: int) -> SearchContent:
    return SearchContent(
        passages=tuple(
            IndexedPassage(
                chunk=Chunk(
                    chunk_id=f"{IDENTIFIER.raw}_{ordinal:04d}",
                    parent_identifier=IDENTIFIER,
                    document_type=DocumentType.ARTICLE,
                    ordinal=ordinal,
                    text=f"passage numéro {ordinal}",
                    tag_path=[],
                    char_start=ordinal * 10,
                    char_end=ordinal * 10 + 10,
                ),
                embedding=[0.1] * DIM,
            )
            for ordinal in range(passage_count)
        )
    )


@pytest.fixture(scope="module")
def opensearch_url():
    container = OpenSearchContainer("opensearchproject/opensearch:3.9.0").with_env(
        "OPENSEARCH_JAVA_OPTS", "-Xms512m -Xmx512m"
    )
    with container:
        config = container.get_config()
        yield f"http://{config['host']}:{config['port']}"


@pytest.fixture
async def search_index(opensearch_url):
    """Un index neuf, créé par ``ensure_index`` comme dans le pipeline."""
    client = create_opensearch_client(opensearch_url)
    repository = OpenSearchSearchIndex(client, INDEX)
    await repository.drop_index()
    await repository.ensure_index()
    yield repository
    await client.close()


async def _stored(search_index: OpenSearchSearchIndex) -> dict:
    client = search_index._client  # noqa: SLF001
    await client.indices.refresh(index=INDEX)
    return await client.get(index=INDEX, id=IDENTIFIER.serialize())


async def _count(search_index: OpenSearchSearchIndex) -> int:
    client = search_index._client  # noqa: SLF001
    await client.indices.refresh(index=INDEX)
    return (await client.count(index=INDEX))["count"]


async def test_ensure_index_est_idempotent(search_index) -> None:
    await search_index.ensure_index()  # la fixture l'a déjà fait une fois

    await search_index.index_document(_doc(), _content(1))
    assert await _count(search_index) == 1


async def test_une_reecriture_REMPLACE_le_document_et_ses_passages(
    search_index,
) -> None:
    """Un article réingéré avec moins de passages ne garde aucun passage périmé."""
    await search_index.index_document(_doc(), _content(5))
    await search_index.index_document(_doc(), _content(3))

    stored = await _stored(search_index)
    assert await _count(search_index) == 1
    assert len(stored["_source"]["passages"]) == 3


async def test_source_garde_les_offsets_mais_ni_le_texte_ni_le_vecteur(
    search_index,
) -> None:
    """Mongo reste le seul stockage du texte (ADR-015)."""
    await search_index.index_document(_doc(), _content(1))

    (passage,) = (await _stored(search_index))["_source"]["passages"]
    assert passage == {
        "chunk_id": f"{IDENTIFIER.raw}_0000",
        "char_start": 0,
        "char_end": 10,
    }


async def test_une_date_mal_formee_fait_echouer_lecriture(search_index) -> None:
    """ADR-028 : l'échec remonte, et la saga compense."""
    with pytest.raises(RequestError):
        await search_index.index_document(
            _doc(metadata={"date_debut": "01/01/2020"}), _content(1)
        )


async def test_un_passage_sans_vecteur_est_accepte(search_index) -> None:
    content = SearchContent(
        passages=(IndexedPassage(chunk=_content(1).passages[0].chunk),)
    )

    await search_index.index_document(_doc(), content)

    assert await _count(search_index) == 1


async def test_supprimer_un_document_meme_ABSENT_ne_leve_rien(search_index) -> None:
    """La compensation peut viser un document jamais écrit."""
    await search_index.index_document(_doc(), _content(1))

    await search_index.delete_document(IDENTIFIER)
    await search_index.delete_document(IDENTIFIER)

    assert await _count(search_index) == 0


async def test_drop_index_epargne_les_autres_index(search_index) -> None:
    """Les index système (Dashboards, plugins) vivent dans le même cluster."""
    client = search_index._client  # noqa: SLF001
    await client.indices.create(index=OTHER_INDEX)

    await search_index.drop_index()

    assert not await client.indices.exists(index=INDEX)
    assert await client.indices.exists(index=OTHER_INDEX)
    await client.indices.delete(index=OTHER_INDEX)


async def test_la_reprise_du_refresh_publie_et_rend_le_reglage_par_defaut(
    search_index,
) -> None:
    client = search_index._client  # noqa: SLF001
    await search_index.suspend_refresh()
    await search_index.index_document(_doc(), _content(1))

    await search_index.resume_refresh()

    settings = await client.indices.get_settings(index=INDEX)
    assert "refresh_interval" not in settings[INDEX]["settings"]["index"]
    assert (await client.count(index=INDEX))["count"] == 1


async def test_force_merge_laisse_un_seul_segment(search_index) -> None:
    client = search_index._client  # noqa: SLF001
    for passage_count in (1, 2, 3):
        await search_index.index_document(_doc(), _content(passage_count))
        await client.indices.refresh(index=INDEX)

    await search_index.force_merge()

    segments = await client.cat.segments(index=INDEX, format="json")
    assert len(segments) == 1
