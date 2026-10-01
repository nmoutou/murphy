"""Qdrant contre la vraie base : un filtre sur un champ mal nommé ne supprime rien et ne
lève rien, et la saga croirait avoir compensé.
"""

import pytest
from testcontainers.qdrant import QdrantContainer

from ragcore.adapters.storage.qdrant.client import create_qdrant_client
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.enums import DocumentType
from ragcore.core.models.identifiers import Identifier

pytestmark = pytest.mark.integration

DIM = 8
COLLECTION = "chunks_test"


def _embedded(document: str, ordinal: int) -> EmbeddedChunk:
    identifier = Identifier(raw=document)
    return EmbeddedChunk(
        chunk=Chunk(
            chunk_id=f"{document}#{ordinal}",
            parent_identifier=identifier,
            document_type=DocumentType.ARTICLE,
            ordinal=ordinal,
            text=f"texte {ordinal}",
            tag_path=[],
            char_start=0,
            char_end=10,
            metadata={},
        ),
        embedding=[0.1] * DIM,
        embedding_model="test",
        embedding_dim=DIM,
    )


@pytest.fixture(scope="module")
def qdrant_url():
    with QdrantContainer("qdrant/qdrant:v1.12.4") as container:
        yield f"http://{container.get_container_host_ip()}:{container.get_exposed_port(6333)}"


@pytest.fixture
async def repo(qdrant_url):
    """Une collection neuve, créée par ``ensure_collection`` comme dans le pipeline :
    c'est un setup de run, pas un effet de bord d'``upsert``."""
    client = create_qdrant_client(qdrant_url)
    if await client.collection_exists(COLLECTION):
        await client.delete_collection(COLLECTION)
    repository = QdrantVectorRepository(client, COLLECTION, DIM)
    await repository.ensure_collection()
    yield repository
    await client.close()


async def _count(repo: QdrantVectorRepository) -> int:
    return (await repo._client.count(COLLECTION)).count  # noqa: SLF001


async def test_ensure_collection_creates_it_and_upsert_stores_the_points(repo) -> None:
    """La collection existe, ``upsert`` écrit."""
    await repo.upsert([_embedded("LEGIARTI000000000001", 0)])

    assert await _count(repo) == 1


async def test_ensure_collection_is_idempotent(repo) -> None:
    """Rejouable : sûr en tête de pipeline, même sur un corpus déjà là."""
    await repo.ensure_collection()  # la fixture l'a déjà fait une fois

    await repo.upsert([_embedded("LEGIARTI000000000001", 0)])
    assert await _count(repo) == 1


async def test_deleting_a_document_removes_only_its_own_vectors(repo) -> None:
    """Le filtre supprime vraiment, et rien de plus."""
    await repo.upsert(
        [
            _embedded("LEGIARTI000000000001", 0),
            _embedded("LEGIARTI000000000001", 1),
            _embedded("LEGIARTI000000000002", 0),
        ]
    )
    assert await _count(repo) == 3

    await repo.delete_by_document(Identifier(raw="LEGIARTI000000000001"))

    # Les 2 chunks du doc 1 sont partis, celui du doc 2 est intact
    assert await _count(repo) == 1


async def test_reupserting_the_same_chunk_does_not_duplicate_it(repo) -> None:
    """Un ID stable : rejouer un run écrase le point au lieu de le dupliquer."""
    await repo.upsert([_embedded("LEGIARTI000000000001", 0)])
    await repo.upsert([_embedded("LEGIARTI000000000001", 0)])

    assert await _count(repo) == 1


async def test_an_empty_upsert_is_a_noop(repo) -> None:
    """Un lot vide ne lève pas et n'écrit rien."""
    await repo.upsert([])

    assert await _count(repo) == 0
