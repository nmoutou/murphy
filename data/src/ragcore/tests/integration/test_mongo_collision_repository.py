"""Les collisions contre un vrai Mongo : un document par source, en parties au-delà du
budget, et rejouer un run remplace les siens."""

from datetime import UTC, datetime

import pytest
from testcontainers.mongodb import MongoDbContainer

from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.collision_repository import (
    MongoCollisionRepository,
)
from ragcore.adapters.storage.mongo.schemas import ensure_meta_indexes
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_collisions import RunCollisions

pytestmark = pytest.mark.integration

DB = "MURPHY_META_TEST"
RUN = RunId("run-1")
STARTED_AT = datetime(2026, 10, 15, tzinfo=UTC)
SMALL_BUDGET = 300
"""De quoi tenir deux détails par partie."""


def _record(source: SourceName, identifier: str) -> CollisionRecord:
    return CollisionRecord(
        source=source,
        reason="facet_root_duplicated",
        identifier=identifier,
        key="ARTICLE",
        files=(f"/data/en_vigueur/{identifier}.xml", f"/data/non/{identifier}.xml"),
    )


@pytest.fixture(scope="module")
def mongo_uri():
    with MongoDbContainer("mongo:7") as container:
        yield container.get_connection_url()


@pytest.fixture
async def client(mongo_uri):
    client = create_mongo_client(mongo_uri)
    await client.drop_database(DB)
    await ensure_meta_indexes(client[DB])
    yield client
    client.close()


async def _stored(repo: MongoCollisionRepository) -> list[dict]:
    cursor = repo._collection.find({}, {"_id": 0}).sort([("source", 1), ("part", 1)])  # noqa: SLF001
    return await cursor.to_list()


async def test_run_source_et_partie_sont_uniques(client) -> None:
    repo = MongoCollisionRepository(client, DB)
    indexes = await repo._collection.index_information()  # noqa: SLF001

    assert indexes["uq_collisions_run_source_part"]["unique"] is True


async def test_un_document_par_source(client) -> None:
    repo = MongoCollisionRepository(client, DB)
    collisions = RunCollisions(
        (_record(SourceName.LEGI, "LEGIARTI1"), _record(SourceName.JADE, "CETATEXT1"))
    )

    await repo.replace_run(RUN, STARTED_AT, collisions)

    documents = await _stored(repo)
    assert [(d["source"], d["part"], d["parts"]) for d in documents] == [
        ("jade", 1, 1),
        ("legi", 1, 1),
    ]


async def test_au_dela_du_budget_la_source_est_decoupee(client) -> None:
    repo = MongoCollisionRepository(client, DB, part_budget_bytes=SMALL_BUDGET)
    records = tuple(_record(SourceName.LEGI, f"LEGIARTI{i}") for i in range(5))

    await repo.replace_run(RUN, STARTED_AT, RunCollisions(records))

    documents = await _stored(repo)
    assert [d["part"] for d in documents] == [1, 2, 3]
    assert {d["collisions"]["facet_root_duplicated"]["count"] for d in documents} == {5}


async def test_rejouer_un_run_remplace_ses_collisions(client) -> None:
    repo = MongoCollisionRepository(client, DB, part_budget_bytes=SMALL_BUDGET)
    many = tuple(_record(SourceName.LEGI, f"LEGIARTI{i}") for i in range(5))
    await repo.replace_run(RUN, STARTED_AT, RunCollisions(many))

    await repo.replace_run(RUN, STARTED_AT, RunCollisions(many[:1]))

    (document,) = await _stored(repo)
    assert document["parts"] == 1
    assert document["started_at"].replace(tzinfo=UTC) == STARTED_AT


async def test_sans_collision_rien_n_est_ecrit(client) -> None:
    repo = MongoCollisionRepository(client, DB)

    await repo.replace_run(RUN, STARTED_AT, RunCollisions())

    assert await _stored(repo) == []
