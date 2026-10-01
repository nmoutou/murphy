"""Le registre des pendantes contre un vrai Mongo : l'unicité n'y tient qu'à un index
déclaré sur des noms de champs écrits à la main.

À trancher sur la vraie base : l'index unique porte sur le bon triplet,
``$setOnInsert`` fige ``first_seen_run``, et le rejeu filtre par ``target_id``.
"""

import pytest
from pymongo.errors import DuplicateKeyError
from testcontainers.mongodb import MongoDbContainer

from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.pending_repository import (
    MongoPendingRelationRepository,
)
from ragcore.adapters.storage.mongo.schemas import (
    ensure_data_indexes,
    reset_data_collections,
)
from ragcore.core.links import CITES
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.pending import PendingRelation

pytestmark = pytest.mark.integration

DB = "MURPHY_DATA_TEST"


def _pending(source: str, target: str, run_id: str) -> PendingRelation:
    return PendingRelation(
        source_id=source,
        target_id=target,
        relation_type=CITES,
        source=SourceName.LEGI,
        metadata={},
        first_seen_run=RunId(run_id),
        last_seen_run=RunId(run_id),
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
    yield MongoPendingRelationRepository(client, DB)
    client.close()


async def test_the_unique_index_covers_the_triplet(repo) -> None:
    """Sans cet index, ``upsert_many`` n'est plus une union."""
    collection = repo._collection  # noqa: SLF001
    indexes = await collection.index_information()

    unique = indexes["uq_pending_source_target_type"]
    assert unique["unique"] is True
    assert [key for key, _ in unique["key"]] == [
        "source_id",
        "target_id",
        "relation_type",
    ]


async def test_seeing_the_same_pending_twice_yields_one_entry(repo) -> None:
    """Dix runs, une seule pendante."""
    await repo.upsert_many([_pending("A", "B", "run-1")])
    await repo.upsert_many([_pending("A", "B", "run-2")])
    await repo.upsert_many([_pending("A", "B", "run-3")])

    assert await repo.count() == 1


async def test_first_seen_run_never_moves_but_last_seen_does(repo) -> None:
    """``first_seen_run`` ne se réécrit pas : c'est la seule trace de depuis quand un
    lien manque."""
    await repo.upsert_many([_pending("A", "B", "run-1")])
    await repo.upsert_many([_pending("A", "B", "run-2")])

    stored = await repo.promotable_for({"B"})

    assert len(stored) == 1
    assert stored[0].first_seen_run == "run-1"
    assert stored[0].last_seen_run == "run-2"


async def test_a_duplicate_insert_is_actually_rejected_by_mongo(repo) -> None:
    """L'index mord : une insertion nue du même triplet échoue."""
    await repo.upsert_many([_pending("A", "B", "run-1")])
    document = _pending("A", "B", "run-9").model_dump(mode="json")

    with pytest.raises(DuplicateKeyError):
        await repo._collection.insert_one(document)  # noqa: SLF001


async def test_the_replay_is_bounded_by_the_delta_not_the_backlog(repo) -> None:
    """Seules les pendantes dont la cible vient d'arriver sont promues."""
    await repo.upsert_many(
        [
            _pending("A", "B", "run-1"),
            _pending("C", "D", "run-1"),
            _pending("E", "F", "run-1"),
        ]
    )

    promotable = await repo.promotable_for({"D"})

    assert len(promotable) == 1
    assert promotable[0].target_id == "D"
    assert await repo.count() == 3  # rien n'a été retiré


async def test_a_promoted_pending_leaves_the_backlog(repo) -> None:
    await repo.upsert_many([_pending("A", "B", "run-1"), _pending("C", "D", "run-1")])

    promotable = await repo.promotable_for({"B"})
    await repo.delete_many([p.key for p in promotable])

    assert await repo.count() == 1


async def test_an_empty_delta_promotes_nothing(repo) -> None:
    """Un run sans nœud écrit ne promeut rien, et ne relit pas le backlog."""
    await repo.upsert_many([_pending("A", "B", "run-1")])

    assert await repo.promotable_for(set()) == []


async def test_the_nuke_empties_the_backlog_and_restores_the_unique_index(repo) -> None:
    """Le nuke efface les pendantes et repose les index, que le drop emporte."""
    await repo.upsert_many([_pending("A", "B", "run-1")])

    await reset_data_collections(repo._collection.database)  # noqa: SLF001

    assert await repo.count() == 0
    indexes = await repo._collection.index_information()  # noqa: SLF001
    assert indexes["uq_pending_source_target_type"]["unique"] is True
