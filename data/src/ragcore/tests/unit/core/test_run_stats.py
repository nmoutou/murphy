"""RunStats se DÉCLARE monoïde commutatif. On le vérifie.

Ce n'est pas de la coquetterie algébrique. Les workers finissent dans un ordre non
déterministe : si ``merge`` n'était pas commutatif, le RunSummary dépendrait de
l'ordonnancement du pool — un non-déterminisme qu'aucun test ne rattraperait, parce
qu'il ne se manifeste qu'en production, sous charge, une fois sur dix.
"""

from ragcore.core.models.run_stats import RunStats

A = RunStats(
    counts={"persisted": 2, "invalidated": 1},
    breakdowns={"invalidated": {"validation_error": 1}},
    unknowns={"field": ["NOTA"]},
)
B = RunStats(
    counts={"persisted": 3},
    breakdowns={"invalidated": {"parse_error": 2}},
    unknowns={"field": ["NOTA", "CONTENU"], "relation_type": ["titre_tm"]},
)
C = RunStats(counts={"promoted": 1}, unknowns={"field": ["LIENS"]})


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


def test_breakdowns_are_summed_per_key() -> None:
    merged = A.merge(B)
    assert merged.breakdowns["invalidated"] == {"validation_error": 1, "parse_error": 2}


def test_unknowns_are_a_deduplicated_union() -> None:
    """Un vocabulaire inconnu est un ENSEMBLE : deux workers qui voient la même
    balise ne la déclarent pas deux fois. Un compteur ici serait un contresens.
    """
    merged = A.merge(B)
    assert merged.unknowns["field"] == ["NOTA", "CONTENU"]
    assert merged.unknowns["relation_type"] == ["titre_tm"]


def test_merge_mutates_nothing() -> None:
    """Les agrégats sont frozen : la fusion RETOURNE, elle n'écrit pas."""
    before = A.model_copy(deep=True)
    A.merge(B)
    assert A == before


def test_reduce_of_nothing_is_empty() -> None:
    assert RunStats.reduce([]) == RunStats.empty()


def test_reduce_folds_every_shard() -> None:
    assert RunStats.reduce([A, B, C]) == A.merge(B).merge(C)
