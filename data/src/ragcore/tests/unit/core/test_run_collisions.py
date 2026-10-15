"""Le détail des collisions se range par source puis par raison, dans un ordre qui ne
dépend pas de celui de la lecture."""

from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.enums import SourceName
from ragcore.core.models.run_collisions import RunCollisions


def _record(source: SourceName, reason: str, identifier: str) -> CollisionRecord:
    return CollisionRecord(
        source=source,
        reason=reason,
        identifier=identifier,
        key="ARTICLE",
        files=(f"{identifier}.xml",),
    )


B_LEGI = _record(SourceName.LEGI, "metadata", "LEGIARTI2")
A_LEGI = _record(SourceName.LEGI, "metadata", "LEGIARTI1")
ROOT_LEGI = _record(SourceName.LEGI, "facet_root_duplicated", "LEGIARTI3")
JADE = _record(SourceName.JADE, "metadata", "CETATEXT1")


def test_rien_a_ranger() -> None:
    assert RunCollisions().by_source() == {}


def test_par_source_puis_par_raison() -> None:
    grouped = RunCollisions((B_LEGI, JADE, ROOT_LEGI)).by_source()

    assert grouped == {
        SourceName.JADE: {"metadata": (JADE,)},
        SourceName.LEGI: {"facet_root_duplicated": (ROOT_LEGI,), "metadata": (B_LEGI,)},
    }


def test_l_ordre_de_lecture_ne_change_rien() -> None:
    forward = RunCollisions((A_LEGI, B_LEGI)).by_source()
    backward = RunCollisions((B_LEGI, A_LEGI)).by_source()

    assert forward == backward
    assert forward[SourceName.LEGI]["metadata"] == (A_LEGI, B_LEGI)
