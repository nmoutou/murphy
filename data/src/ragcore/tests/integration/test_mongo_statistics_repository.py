"""Les statistiques contre un vrai Mongo : un document par run, rejouer le remplace."""

from datetime import UTC, datetime

import pytest
from testcontainers.mongodb import MongoDbContainer

from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.schemas import ensure_meta_indexes
from ragcore.adapters.storage.mongo.statistics_repository import (
    MongoStatisticsRepository,
)
from ragcore.core.models.distribution import Distribution
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_measures import RunMeasures
from ragcore.core.models.run_statistics import RunStatistics

pytestmark = pytest.mark.integration

DB = "MURPHY_META_TEST"


def _statistics(chunks: int) -> RunStatistics:
    return RunStatistics(
        run_id=RunId("run-1"),
        started_at=datetime(2026, 10, 14, tzinfo=UTC),
        stages_s={"phase1": 12.5},
        measures=RunMeasures(
            {("documents", "legi", "chunks"): Distribution.of(chunks, "LEGIARTI1")}
        ),
    )


@pytest.fixture(scope="module")
def mongo_uri():
    with MongoDbContainer("mongo:7") as container:
        yield container.get_connection_url()


@pytest.fixture
async def repo(mongo_uri):
    client = create_mongo_client(mongo_uri)
    await client.drop_database(DB)
    await ensure_meta_indexes(client[DB])
    yield MongoStatisticsRepository(client, DB)
    client.close()


async def test_the_run_id_is_unique(repo) -> None:
    indexes = await repo._collection.index_information()  # noqa: SLF001

    assert indexes["uq_statistics_run_id"]["unique"] is True


async def test_replaying_a_run_replaces_its_statistics(repo) -> None:
    await repo.upsert(_statistics(chunks=3))
    await repo.upsert(_statistics(chunks=8))

    documents = await repo._collection.find({}, {"_id": 0}).to_list()  # noqa: SLF001

    (document,) = documents
    assert document["stages_s"] == {"phase1": 12.5}
    assert document["documents"]["legi"]["chunks"]["max"] == 8
