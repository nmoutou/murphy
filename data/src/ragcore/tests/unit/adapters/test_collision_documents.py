"""Un document par source, découpé en parties au-delà du budget : chaque partie garde les
comptes de la source entière, et aucun détail n'est perdu ni dupliqué."""

import bson

from ragcore.adapters.storage.mongo.collision_documents import source_documents
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.enums import SourceName

HEADER = {"run_id": "run-1", "source": "legi"}


def _record(reason: str, index: int) -> CollisionRecord:
    return CollisionRecord(
        source=SourceName.LEGI,
        reason=reason,
        identifier=f"LEGIARTI{index:012d}",
        key="ARTICLE",
        files=(f"/data/en_vigueur/{index}.xml", f"/data/non_vigueur/{index}.xml"),
    )


COLLISIONS = {
    "facet_root_duplicated": tuple(
        _record("facet_root_duplicated", i) for i in range(3)
    ),
    "metadata": tuple(_record("metadata", i) for i in range(3, 5)),
}
DETAIL_BYTES = len(bson.encode(COLLISIONS["metadata"][0].to_detail()))


def test_sous_le_budget_une_seule_partie() -> None:
    (document,) = source_documents(HEADER, COLLISIONS)

    assert (document["run_id"], document["part"], document["parts"]) == ("run-1", 1, 1)
    assert document["collisions"]["metadata"] == {
        "count": 2,
        "details": [record.to_detail() for record in COLLISIONS["metadata"]],
    }


def test_au_dela_du_budget_des_parties_numerotees() -> None:
    documents = source_documents(HEADER, COLLISIONS, budget_bytes=2 * DETAIL_BYTES)

    assert [(d["part"], d["parts"]) for d in documents] == [(1, 3), (2, 3), (3, 3)]
    for document in documents:
        counts = {r: c["count"] for r, c in document["collisions"].items()}
        assert counts == {"facet_root_duplicated": 3, "metadata": 2}
    spread = [
        detail
        for document in documents
        for found in document["collisions"].values()
        for detail in found["details"]
    ]
    expected = [r.to_detail() for found in COLLISIONS.values() for r in found]
    assert sorted(spread, key=str) == sorted(expected, key=str)


def test_un_detail_plus_gros_que_le_budget_a_sa_partie() -> None:
    documents = source_documents(HEADER, COLLISIONS, budget_bytes=1)

    assert len(documents) == 5
