"""RunStats se DÉCLARE monoïde commutatif. On le vérifie.

Ce n'est pas de la coquetterie algébrique. Les workers finissent dans un ordre non
déterministe : si ``merge`` n'était pas commutatif, le RunSummary dépendrait de
l'ordonnancement du pool — un non-déterminisme qu'aucun test ne rattraperait, parce
qu'il ne se manifeste qu'en production, sous charge, une fois sur dix.
"""

from ragcore.core.models.collision_tally import CollisionExample, CollisionTally
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally

DOC_1 = UnknownExample(identifier="LEGIARTI000000000001", source_file="a.xml")
DOC_2 = UnknownExample(identifier="LEGIARTI000000000002", source_file="b.xml")
TWO_FILES = CollisionExample(source_files=("a.xml", "b.xml"))
ONE_FILE = CollisionExample(source_files=("b.xml",))


def _tally(count: int, example: UnknownExample) -> UnknownTally:
    return UnknownTally(count=count, example=example)


A = RunStats(
    counts={"persisted": 2, "invalidated": 1},
    unknowns={"field": {"NOTA": _tally(1, DOC_2)}},
    collisions={"url": CollisionTally(count=1, example=ONE_FILE)},
)
B = RunStats(
    counts={"persisted": 3},
    unknowns={
        "field": {"NOTA": _tally(2, DOC_1), "CONTENU": _tally(1, DOC_2)},
        "relation_type": {"titre_tm": _tally(1, DOC_1)},
    },
    collisions={
        "url": CollisionTally(count=2, example=TWO_FILES),
        "num": CollisionTally(count=1, example=ONE_FILE),
    },
)
C = RunStats(counts={"promoted": 1}, unknowns={"field": {"LIENS": _tally(1, DOC_1)}})


def test_empty_is_the_neutral_element() -> None:
    assert A.merge(RunStats.empty()) == A
    assert RunStats.empty().merge(A) == A


def test_merge_is_associative() -> None:
    assert A.merge(B).merge(C) == A.merge(B.merge(C))


def test_merge_is_commutative() -> None:
    """La loi qui protège du non-déterminisme : l'ordre des workers n'importe pas."""
    assert A.merge(B) == B.merge(A)


def test_counts_are_summed() -> None:
    merged = A.merge(B)
    assert merged.counts["persisted"] == 5
    assert merged.counts["invalidated"] == 1


def test_unknowns_count_the_documents_of_every_worker() -> None:
    """Un inconnu se compte en documents : deux workers qui le voient additionnent."""
    merged = A.merge(B)
    assert merged.unknowns["field"]["NOTA"].count == 3
    assert merged.unknowns["field"]["CONTENU"].count == 1
    assert merged.unknowns["relation_type"]["titre_tm"].count == 1


def test_the_example_kept_is_the_smallest_whatever_the_order() -> None:
    """« Le premier vu » dépendrait de l'ordre de fin des workers : on garde le plus
    petit exemple, et la fusion reste commutative."""
    assert A.merge(B).unknowns["field"]["NOTA"].example == DOC_1
    assert B.merge(A).unknowns["field"]["NOTA"].example == DOC_1


def test_with_unknown_counts_one_document() -> None:
    stats = RunStats.empty().with_unknown("field", "NOTA", DOC_2)
    stats = stats.with_unknown("field", "NOTA", DOC_1)

    assert stats.unknowns == {"field": {"NOTA": _tally(2, DOC_1)}}


def test_merge_mutates_nothing() -> None:
    """Les agrégats sont frozen : la fusion RETOURNE, elle n'écrit pas."""
    before = A.model_copy(deep=True)
    A.merge(B)
    assert A == before


def test_reduce_of_nothing_is_empty() -> None:
    assert RunStats.reduce([]) == RunStats.empty()


def test_reduce_folds_every_shard() -> None:
    assert RunStats.reduce([A, B, C]) == A.merge(B).merge(C)


def test_collisions_count_the_documents_of_every_worker() -> None:
    merged = A.merge(B)
    assert merged.collisions["url"].count == 3
    assert merged.collisions["num"].count == 1


def test_the_collision_example_kept_is_the_smallest_whatever_the_order() -> None:
    assert A.merge(B).collisions["url"].example == TWO_FILES
    assert B.merge(A).collisions["url"].example == TWO_FILES


def test_with_collision_counts_one_document() -> None:
    stats = RunStats.empty().with_collision("url", ONE_FILE)
    stats = stats.with_collision("url", TWO_FILES)

    assert stats.collisions == {"url": CollisionTally(count=2, example=TWO_FILES)}
    assert stats.unknowns == {}
