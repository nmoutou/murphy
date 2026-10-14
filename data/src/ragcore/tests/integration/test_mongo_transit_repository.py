"""Les relations en transit contre un vrai Mongo : l'index déclaré, la sérialisation
aller-retour, la compensation à la maille (document, run)."""

import pytest
from testcontainers.mongodb import MongoDbContainer

from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.schemas import ensure_data_indexes
from ragcore.adapters.storage.mongo.transit_repository import (
    MongoTransitRelationRepository,
)
from ragcore.core.links import CITE, CONTIENT
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.relation import Relation

pytestmark = pytest.mark.integration

DB = "MURPHY_DATA_TEST"
RUN = RunId("run-1")
OTHER_RUN = RunId("run-0")


def _relation(source: str, target: str, verb: str = CITE) -> Relation:
    return Relation(
        source_identifier=Identifier(raw=source),
        target_identifier=Identifier(raw=target),
        relation_type=verb,
        source=SourceName.LEGI,
        metadata={"typelien": "CITATION"},
    )


A, B, C = "LEGIARTI000000000001", "LEGIARTI000000000002", "LEGISCTA000000000003"


@pytest.fixture(scope="module")
def mongo_uri():
    with MongoDbContainer("mongo:7") as container:
        yield container.get_connection_url()


@pytest.fixture
async def repo(mongo_uri):
    client = create_mongo_client(mongo_uri)
    await client.drop_database(DB)
    await ensure_data_indexes(client[DB])
    yield MongoTransitRelationRepository(client, DB)
    client.close()


async def test_the_index_covers_run_type_and_source(repo) -> None:
    indexes = await repo._collection.index_information()  # noqa: SLF001

    index = indexes["idx_transit_run_type_source"]
    assert [field for field, _ in index["key"]] == [
        "run_id",
        "relation_type",
        "source_id",
    ]
    assert not index.get("unique", False)


async def test_a_relation_comes_back_as_it_went_in(repo) -> None:
    """Une arête déclarée deux fois donne deux lignes : la réduction dédoublonne."""
    relations = [_relation(A, B), _relation(A, B), _relation(C, A, CONTIENT)]

    await repo.insert_many(relations, RUN)

    assert sorted(await repo.read_run(RUN), key=repr) == sorted(relations, key=repr)


async def test_the_compensation_removes_the_document_of_this_run_only(repo) -> None:
    await repo.insert_many([_relation(A, B), _relation(C, A, CONTIENT)], RUN)
    await repo.insert_many([_relation(A, C)], OTHER_RUN)

    await repo.delete_for_source(Identifier(raw=A), RUN)

    assert await repo.read_run(RUN) == [_relation(C, A, CONTIENT)]
    assert await repo.read_run(OTHER_RUN) == [_relation(A, C)]


async def test_clear_and_delete_run(repo) -> None:
    await repo.insert_many([_relation(A, B)], RUN)
    await repo.insert_many([_relation(A, C)], OTHER_RUN)

    await repo.delete_run(RUN)
    assert await repo.count() == 1

    await repo.clear()
    assert await repo.count() == 0
