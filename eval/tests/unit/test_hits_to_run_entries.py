from __future__ import annotations

from murphy_eval.adapters.retrieval.baseline import hits_to_run_entries
from murphy_eval.adapters.retrieval.hits import Hit


def _hits() -> list[Hit]:
    # Déjà triés par score décroissant (contrat Qdrant).
    return [
        Hit(chunk_id="c1", identifier="eli:LEGIARTI000000000001", score=0.9),
        Hit(chunk_id="c2", identifier="decision:JURITEXT000000000002", score=0.7),
        Hit(chunk_id="c3", identifier="eli:LEGIARTI000000000003", score=0.5),
    ]


def test_doc_id_vient_de_identifier_sans_transformation() -> None:
    """ADR-018 : le doc_id est l'``identifier`` du payload, écrit tel quel."""
    entries = hits_to_run_entries("q1", _hits(), min_score=None, run_tag="baseline")
    assert [e.doc_id for e in entries] == [
        "eli:LEGIARTI000000000001",
        "decision:JURITEXT000000000002",
        "eli:LEGIARTI000000000003",
    ]


def test_rang_est_la_position_1_a_n_contigue() -> None:
    entries = hits_to_run_entries("q1", _hits(), min_score=None, run_tag="baseline")
    assert [e.rank for e in entries] == [1, 2, 3]
    assert [e.chunk_id for e in entries] == ["c1", "c2", "c3"]
    assert [e.score for e in entries] == [0.9, 0.7, 0.5]


def test_min_score_filtre_puis_renumerote_de_facon_contigue() -> None:
    """Le seuil s'applique avant le rang : les rangs restent 1..n, sans trou."""
    entries = hits_to_run_entries("q1", _hits(), min_score=0.6, run_tag="baseline")
    assert [e.chunk_id for e in entries] == ["c1", "c2"]
    assert [e.rank for e in entries] == [1, 2]


def test_run_tag_est_propage() -> None:
    entries = hits_to_run_entries("q1", _hits(), min_score=None, run_tag="W1xR1")
    assert {e.run_tag for e in entries} == {"W1xR1"}


def test_query_id_est_propage() -> None:
    entries = hits_to_run_entries("q42", _hits(), min_score=None, run_tag="baseline")
    assert {e.query_id for e in entries} == {"q42"}


def test_aucun_hit_donne_une_liste_vide() -> None:
    assert hits_to_run_entries("q1", [], min_score=None, run_tag="baseline") == []


def test_min_score_ecarte_tout_donne_une_liste_vide() -> None:
    entries = hits_to_run_entries("q1", _hits(), min_score=1.0, run_tag="baseline")
    assert entries == []
