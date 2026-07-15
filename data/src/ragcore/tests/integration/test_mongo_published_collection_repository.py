"""Le pointeur de collection contre un VRAI Mongo.

Le pointeur est un **singleton** : « quelle collection fait foi ? » n'a qu'une réponse.
Cette unicité n'est pas donnée par la structure — elle est donnée par un
``replace_one`` sur une clé fixe, et par rien d'autre. Si l'``upsert`` empilait au lieu
de remplacer, ``get()`` rendrait *un* document au hasard parmi N, et le serving lirait
une collection périmée sans que rien ne lève.

C'est le genre d'affirmation qu'un fake indexé par clé ne peut pas trancher : chez lui
l'unicité est gratuite.
"""

import pytest
from testcontainers.mongodb import MongoDbContainer

from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.published_collection_repository import (
    MongoPublishedCollectionRepository,
)
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.published_collection import PublishedCollection

pytestmark = pytest.mark.integration

DB = "MURPHY_META_TEST"


@pytest.fixture(scope="module")
def mongo_uri():
    with MongoDbContainer("mongo:7") as container:
        yield container.get_connection_url()


@pytest.fixture
async def repo(mongo_uri):
    client = create_mongo_client(mongo_uri)
    await client[DB].drop_collection("meta_published_collection")
    yield MongoPublishedCollectionRepository(client, DB)
    client.close()


async def test_no_pointer_yet_is_not_an_error(repo) -> None:
    """Aucun run `ok` n'a encore publié. C'est un état légitime, pas une panne."""
    assert await repo.get() is None


async def test_publishing_then_reading_gives_the_collection_back(repo) -> None:
    await repo.publish(
        PublishedCollection.of("9424808d", run_id=RunId("r-1"), document_count=1121)
    )

    published = await repo.get()

    assert published is not None
    assert published.collection_name == "9424808d"
    assert published.document_count == 1121
    assert published.run_id == "r-1"


async def test_publishing_twice_REPLACES_and_never_stacks(repo) -> None:
    """LE test : le pointeur est un singleton, pas un journal.

    S'il empilait, ``get()`` rendrait un document au hasard parmi N — et le serving
    pourrait lire une collection périmée, en silence. L'historique des runs vit dans les
    ``RunSummary`` ; le pointeur, lui, n'a pas de passé.
    """
    await repo.publish(
        PublishedCollection.of("ancienne", run_id=RunId("r-1"), document_count=10)
    )
    await repo.publish(
        PublishedCollection.of("nouvelle", run_id=RunId("r-2"), document_count=1121)
    )

    published = await repo.get()
    assert published is not None
    assert published.collection_name == "nouvelle"

    # Et il n'y a qu'UN document en base — pas deux.
    count = await repo._collection.count_documents({})  # noqa: SLF001
    assert count == 1
