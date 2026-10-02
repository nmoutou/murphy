"""Les relations non formatées contre un vrai Mongo : l'unicité n'y tient qu'à l'index.

À trancher sur la vraie base : l'index porte sur la clé à quatre champs,
``$setOnInsert`` fige ``first_seen_run``, deux ``sens`` opposés font deux lignes, et la
compensation épargne ce qu'un run précédent a écrit.
"""

import pytest
from pymongo.errors import DuplicateKeyError
from testcontainers.mongodb import MongoDbContainer

from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.schemas import (
    ensure_data_indexes,
    reset_data_collections,
)
from ragcore.adapters.storage.mongo.unformatted_repository import (
    MongoUnformattedRelationRepository,
)
from ragcore.core.links import CITE
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.unformatted_relation import UnformattedRelation

pytestmark = pytest.mark.integration

DB = "MURPHY_DATA_TEST"
CITING = Identifier(raw="JURITEXT000000000001")
RUN_1 = RunId("run-1")
RUN_2 = RunId("run-2")


def _unformatted(target_text: str, sens: str = "source") -> UnformattedRelation:
    return UnformattedRelation(
        source_identifier=CITING,
        target_text=target_text,
        relation_type=CITE,
        sens=sens,
        source=SourceName.CASS,
    )


@pytest.fixture(scope="module")
def mongo_uri():
    with MongoDbContainer("mongo:7") as container:
        yield container.get_connection_url()


@pytest.fixture
async def repo(mongo_uri):
    client = create_mongo_client(mongo_uri)
    await client.drop_database(DB)
    await ensure_data_indexes(client[DB])
    yield MongoUnformattedRelationRepository(client, DB)
    client.close()


async def _stored(repo: MongoUnformattedRelationRepository) -> list[dict]:
    collection = repo._collection  # noqa: SLF001
    return [doc async for doc in collection.find({}, {"_id": 0})]


async def test_the_unique_index_covers_the_four_fields(repo) -> None:
    """Sans cet index, ``upsert_many`` n'est plus une union."""
    indexes = await repo._collection.index_information()  # noqa: SLF001

    unique = indexes["uq_unformatted_source_text_type_sens"]
    assert unique["unique"] is True
    assert [key for key, _ in unique["key"]] == [
        "source_id",
        "target_text",
        "relation_type",
        "sens",
    ]


async def test_the_written_row_has_the_agreed_schema(repo) -> None:
    """Le schéma d'ADR-021, champ par champ : celui que la résolution lira."""
    await repo.upsert_many(
        [_unformatted("Articles 1103 et 1229 du code civil.")], RUN_1
    )

    assert await _stored(repo) == [
        {
            "source_id": "JURITEXT000000000001",
            "target_text": "Articles 1103 et 1229 du code civil.",
            "relation_type": "cite",
            "sens": "source",
            "source": "cass",
            "last_seen_run": "run-1",
            "first_seen_run": "run-1",
        }
    ]


async def test_first_seen_run_never_moves_but_last_seen_does(repo) -> None:
    """Deux runs, une ligne, née au premier, revue au second."""
    await repo.upsert_many([_unformatted("code civil")], RUN_1)
    await repo.upsert_many([_unformatted("code civil")], RUN_2)

    [row] = await _stored(repo)
    assert row["first_seen_run"] == "run-1"
    assert row["last_seen_run"] == "run-2"


async def test_opposite_sens_are_two_facts(repo) -> None:
    """« Je cite X » et « X me cite » : le ``$set`` n'écrase pas l'un par l'autre."""
    await repo.upsert_many(
        [_unformatted("code civil", "source"), _unformatted("code civil", "cible")],
        RUN_1,
    )

    assert await repo.count() == 2


async def test_a_duplicate_insert_is_actually_rejected_by_mongo(repo) -> None:
    """L'index mord : une insertion nue du même enregistrement échoue."""
    await repo.upsert_many([_unformatted("code civil")], RUN_1)
    [row] = await _stored(repo)

    with pytest.raises(DuplicateKeyError):
        await repo._collection.insert_one(row)  # noqa: SLF001


async def test_the_compensation_spares_the_rows_of_earlier_runs(repo) -> None:
    """La saga qui échoue au run 2 ne défait que ce que le run 2 a créé."""
    await repo.upsert_many([_unformatted("code civil")], RUN_1)
    await repo.upsert_many(
        [_unformatted("code civil"), _unformatted("code pénal")], RUN_2
    )

    await repo.delete_first_seen(CITING, RUN_2)

    [row] = await _stored(repo)
    assert row["target_text"] == "code civil"
    assert row["first_seen_run"] == "run-1"


async def test_the_nuke_empties_the_collection_and_restores_the_unique_index(
    repo,
) -> None:
    """La remise à neuf repose les index, que le drop emporte."""
    await repo.upsert_many([_unformatted("code civil")], RUN_1)

    await reset_data_collections(repo._collection.database)  # noqa: SLF001

    assert await repo.count() == 0
    indexes = await repo._collection.index_information()  # noqa: SLF001
    assert indexes["uq_unformatted_source_text_type_sens"]["unique"] is True
