"""Les problèmes contre un vrai Mongo : une ligne par problème, sous son `run_id`, par
lots, et les runs successifs s'accumulent."""

from datetime import datetime

import pytest
from testcontainers.mongodb import MongoDbContainer

from ragcore.adapters.storage.mongo import problem_repository
from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.problem_repository import (
    COLLISIONS_COLLECTION,
    MISMATCH_COLLECTION,
    SUPERSEDED_COLLECTION,
    UNREADABLE_COLLECTION,
    MongoProblemRepository,
)
from ragcore.adapters.storage.mongo.schemas import (
    ensure_problems_indexes,
    reset_problem_collections,
)
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.problems import (
    CopyStamp,
    MismatchedFile,
    SupersededCopy,
    UnreadableFile,
)

pytestmark = pytest.mark.integration

DB = "MURPHY_PROBLEMS_TEST"
RUN_1 = RunId("run-1")
RUN_2 = RunId("run-2")


def _collision(identifier: str) -> CollisionRecord:
    return CollisionRecord(
        source=SourceName.LEGI,
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
async def database(mongo_uri):
    client = create_mongo_client(mongo_uri)
    await client.drop_database(DB)
    await ensure_problems_indexes(client[DB])
    yield client[DB]
    client.close()


async def _rows(database, collection: str) -> list[dict]:
    return [row async for row in database[collection].find({}, {"_id": 0})]


async def test_une_collision_donne_une_ligne_a_plat(database) -> None:
    repo = MongoProblemRepository(database.client, DB)

    await repo.insert_run(RUN_1, [_collision("LEGIARTI1")])

    assert await _rows(database, COLLISIONS_COLLECTION) == [
        {
            "run_id": "run-1",
            "source": "legi",
            "reason": "facet_root_duplicated",
            "identifier": "LEGIARTI1",
            "key": "ARTICLE",
            "files": [
                "/data/en_vigueur/LEGIARTI1.xml",
                "/data/non/LEGIARTI1.xml",
            ],
        }
    ]


async def test_une_copie_ecartee_est_datee_a_la_milliseconde(database) -> None:
    kept_ns = 1_760_000_000_123_456_789
    copy = SupersededCopy(
        source=SourceName.LEGI,
        identifier="LEGIARTI1",
        root="ARTICLE",
        kept=CopyStamp(path="/non_vigueur/LEGIARTI1.xml", mtime_ns=kept_ns),
        discarded=CopyStamp(path="/en_vigueur/LEGIARTI1.xml", mtime_ns=0),
    )
    repo = MongoProblemRepository(database.client, DB)

    await repo.insert_run(RUN_1, [_collision("LEGIARTI1"), copy])

    (row,) = await _rows(database, SUPERSEDED_COLLECTION)
    assert row["kept"] == {
        "path": "/non_vigueur/LEGIARTI1.xml",
        "mtime": datetime(2025, 10, 9, 8, 53, 20, 123000),
    }
    assert row["discarded"]["mtime"] == datetime(1970, 1, 1)
    assert (row["run_id"], row["identifier"], row["root"]) == (
        "run-1",
        "LEGIARTI1",
        "ARTICLE",
    )
    assert await database[COLLISIONS_COLLECTION].count_documents({}) == 1


async def test_les_fichiers_ecartes_ont_chacun_leur_collection(database) -> None:
    unreadable = UnreadableFile(
        source=SourceName.LEGI,
        key="LEGIARTI1",
        path="/legi/LEGIARTI1.xml",
        error="no element found: line 1, column 9",
    )
    mismatch = MismatchedFile(
        source=SourceName.LEGI, key="versions", path="/legi/versions.xml", found_id=None
    )
    repo = MongoProblemRepository(database.client, DB)

    await repo.insert_run(RUN_1, [unreadable, mismatch])

    assert await _rows(database, UNREADABLE_COLLECTION) == [
        {
            "run_id": "run-1",
            "source": "legi",
            "key": "LEGIARTI1",
            "path": "/legi/LEGIARTI1.xml",
            "error": "no element found: line 1, column 9",
        }
    ]
    assert await _rows(database, MISMATCH_COLLECTION) == [
        {
            "run_id": "run-1",
            "source": "legi",
            "key": "versions",
            "path": "/legi/versions.xml",
            "found_id": None,
        }
    ]


async def test_les_lignes_partent_par_lots(
    database, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(problem_repository, "INSERT_BATCH_SIZE", 2)
    repo = MongoProblemRepository(database.client, DB)

    await repo.insert_run(RUN_1, [_collision(f"LEGIARTI{n}") for n in range(5)])

    assert await database[COLLISIONS_COLLECTION].count_documents({}) == 5


async def test_les_runs_successifs_s_accumulent(database) -> None:
    repo = MongoProblemRepository(database.client, DB)

    await repo.insert_run(RUN_1, [_collision("LEGIARTI1")])
    await repo.insert_run(RUN_2, [_collision("LEGIARTI1")])

    runs = {row["run_id"] for row in await _rows(database, COLLISIONS_COLLECTION)}
    assert runs == {"run-1", "run-2"}


async def test_un_run_sans_probleme_n_ecrit_rien(database) -> None:
    repo = MongoProblemRepository(database.client, DB)

    await repo.insert_run(RUN_1, [])

    assert await database[COLLISIONS_COLLECTION].count_documents({}) == 0


async def test_le_nuke_vide_et_repose_les_index(database) -> None:
    repo = MongoProblemRepository(database.client, DB)
    await repo.insert_run(RUN_1, [_collision("LEGIARTI1")])

    await reset_problem_collections(database)

    assert await database[COLLISIONS_COLLECTION].count_documents({}) == 0
    indexes = await database[COLLISIONS_COLLECTION].index_information()
    assert {"idx_collisions_run_source_reason", "idx_collisions_identifier"} <= set(
        indexes
    )
