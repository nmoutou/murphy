"""Qdrant, contre la vraie base — parce qu'un filtre qui ne matche rien ne LÈVE rien.

C'est la mécanique du silence, une troisième fois : ``delete`` avec un
``FieldCondition`` sur un champ de payload qui n'existe pas (ou mal nommé) réussit,
retourne un statut OK, et ne supprime **rien**. La saga croirait avoir compensé.
Les vecteurs de l'ancien document resteraient, et la recherche les remonterait
comme s'ils étaient à jour.

Aucun test unitaire ne peut trancher : il faudrait rejouer le moteur de filtre de
Qdrant, c'est-à-dire réécrire Qdrant.
"""

import pytest
from testcontainers.qdrant import QdrantContainer

from ragcore.adapters.storage.qdrant.client import create_qdrant_client
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.identifiers import ELI, OwnerId

pytestmark = pytest.mark.integration

OWNER = OwnerId("owner-1")
OTHER_OWNER = OwnerId("owner-2")
DIM = 8
COLLECTION = "chunks_test"


def _embedded(
    document: str, ordinal: int, owner: OwnerId = OWNER
) -> EmbeddedChunk:
    identifier = ELI(raw=document)
    return EmbeddedChunk(
        chunk=Chunk(
            chunk_id=f"{document}#{ordinal}#{owner}",
            parent_identifier=identifier,
            owner_id=owner,
            ordinal=ordinal,
            text=f"texte {ordinal}",
            structural_path=[],
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
    client = create_qdrant_client(qdrant_url)
    if await client.collection_exists(COLLECTION):
        await client.delete_collection(COLLECTION)
    yield QdrantVectorRepository(client, COLLECTION, DIM)
    await client.close()


async def _count(repo: QdrantVectorRepository) -> int:
    return (await repo._client.count(COLLECTION)).count  # noqa: SLF001


async def test_upsert_creates_the_collection_and_stores_the_points(repo) -> None:
    await repo.upsert([_embedded("LEGIARTI000000000001", 0)])

    assert await _count(repo) == 1


async def test_deleting_a_document_removes_only_its_own_vectors(repo) -> None:
    """LE test : le filtre supprime-t-il vraiment, et RIEN de plus ?

    Un ``FieldCondition`` mal nommé ne lèverait pas — il ne supprimerait rien, et la
    compensation de la saga serait une illusion.
    """
    await repo.upsert(
        [
            _embedded("LEGIARTI000000000001", 0),
            _embedded("LEGIARTI000000000001", 1),
            _embedded("LEGIARTI000000000002", 0),
        ]
    )
    assert await _count(repo) == 3

    await repo.delete_by_document(ELI(raw="LEGIARTI000000000001"), OWNER)

    # Les 2 chunks du doc 1 sont partis, celui du doc 2 est intact.
    assert await _count(repo) == 1


async def test_deleting_never_crosses_owners(repo) -> None:
    """Le même document, chez deux propriétaires. Supprimer chez l'un ne doit pas
    toucher l'autre — sinon un run effacerait le corpus d'un tiers, en silence.
    """
    await repo.upsert(
        [
            _embedded("LEGIARTI000000000001", 0, owner=OWNER),
            _embedded("LEGIARTI000000000001", 0, owner=OTHER_OWNER),
        ]
    )
    assert await _count(repo) == 2

    await repo.delete_by_document(ELI(raw="LEGIARTI000000000001"), OWNER)

    assert await _count(repo) == 1


async def test_reupserting_the_same_chunk_does_not_duplicate_it(repo) -> None:
    """L'ID est un hash STABLE du chunk_id (sha256, pas ``hash()``). Rejouer un run
    doit écraser le point, pas en créer un second — sinon la recherche remonterait
    deux fois le même passage.
    """
    await repo.upsert([_embedded("LEGIARTI000000000001", 0)])
    await repo.upsert([_embedded("LEGIARTI000000000001", 0)])

    assert await _count(repo) == 1


async def test_an_empty_upsert_is_a_noop(repo) -> None:
    await repo.upsert([])  # ne doit pas créer la collection ni lever
