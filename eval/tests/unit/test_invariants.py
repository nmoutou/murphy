from __future__ import annotations

from murphy_eval.core.models.judgment import Judgment, Qrels
from murphy_eval.core.models.run import Run, RunEntry
from murphy_eval.core.services.invariants import (
    InvariantError,
    Violation,
    check_qrels,
    check_run,
    check_run_against_qrels,
)


def _entry(query_id: str, chunk_id: str, doc_id: str, rank: int) -> RunEntry:
    return RunEntry(
        query_id=query_id, chunk_id=chunk_id, doc_id=doc_id, rank=rank, score=1.0
    )


# --- check_run -------------------------------------------------------------


def test_run_sain_ne_produit_aucune_violation() -> None:
    run = Run(
        entries=(
            _entry("q1", "c1", "eli:D1", 1),
            _entry("q1", "c2", "eli:D2", 2),
            _entry("q2", "c3", "decision:D3", 1),
        )
    )
    assert check_run(run) == []


def test_rangs_non_contigus_signales() -> None:
    run = Run(
        entries=(_entry("q1", "c1", "eli:D1", 1), _entry("q1", "c2", "eli:D2", 3))
    )
    violations = check_run(run)
    assert [v.invariant for v in violations] == ["ranks_contiguous"]
    assert violations[0].query_id == "q1"


def test_rangs_dupliques_signales_avant_contiguite() -> None:
    """Un rang dupliqué est diagnostiqué comme tel (pas comme un trou)."""
    run = Run(
        entries=(_entry("q1", "c1", "eli:D1", 1), _entry("q1", "c2", "eli:D2", 1))
    )
    violations = check_run(run)
    assert [v.invariant for v in violations] == ["ranks_unique"]


def test_chunk_id_duplique_dans_une_requete_signale() -> None:
    run = Run(
        entries=(_entry("q1", "c1", "eli:D1", 1), _entry("q1", "c1", "eli:D1", 2))
    )
    invariants = {v.invariant for v in check_run(run)}
    assert "no_duplicate_chunk" in invariants


def test_doc_id_vide_signale() -> None:
    run = Run(entries=(_entry("q1", "c1", "", 1),))
    assert [v.invariant for v in check_run(run)] == ["well_formed_id"]


def test_chunk_id_a_blanc_de_bord_signale() -> None:
    run = Run(entries=(_entry("q1", " c1 ", "eli:D1", 1),))
    assert [v.invariant for v in check_run(run)] == ["well_formed_id"]


def test_chunk_id_avec_deux_doc_id_signale() -> None:
    """Même chunk rattaché à deux documents : agrégation chunk→document faussée."""
    run = Run(
        entries=(_entry("q1", "c1", "eli:D1", 1), _entry("q1", "c1", "eli:D2", 2))
    )
    assert "consistent_chunk_doc" in {v.invariant for v in check_run(run)}


def test_chunk_id_meme_doc_id_a_travers_requetes_ne_signale_rien() -> None:
    """Le contrôle est intra-requête : le même (chunk, doc) sur q1 et q2 est sain."""
    run = Run(
        entries=(_entry("q1", "c1", "eli:D1", 1), _entry("q2", "c1", "eli:D1", 1))
    )
    assert check_run(run) == []


def test_les_violations_sont_collectees_pas_arretees_a_la_premiere() -> None:
    """Deux requêtes fautives -> deux violations, une suite dit tout d'un coup."""
    run = Run(
        entries=(
            _entry("q1", "c1", "eli:D1", 2),  # rang non contigu
            _entry("q2", "c2", "", 1),  # doc_id vide
        )
    )
    invariants = sorted(v.invariant for v in check_run(run))
    assert invariants == ["ranks_contiguous", "well_formed_id"]


# --- check_qrels -----------------------------------------------------------


def test_qrels_sains_ne_produisent_aucune_violation() -> None:
    qrels = Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="eli:D1", chunk_id="c1", grade=3),
            Judgment(query_id="q1", doc_id="eli:D2", chunk_id="c2", grade=1),
        )
    )
    assert check_qrels(qrels) == []


def test_qrels_chunk_juge_deux_fois_signale() -> None:
    qrels = Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="eli:D1", chunk_id="c1", grade=3),
            Judgment(query_id="q1", doc_id="eli:D1", chunk_id="c1", grade=1),
        )
    )
    assert [v.invariant for v in check_qrels(qrels)] == ["no_duplicate_chunk"]


def test_qrels_doc_id_vide_signale() -> None:
    qrels = Qrels(
        judgments=(Judgment(query_id="q1", doc_id="", chunk_id="c1", grade=3),)
    )
    assert [v.invariant for v in check_qrels(qrels)] == ["well_formed_id"]


def test_qrels_chunk_id_a_blanc_de_bord_signale() -> None:
    qrels = Qrels(
        judgments=(Judgment(query_id="q1", doc_id="eli:D1", chunk_id=" c1 ", grade=3),)
    )
    assert [v.invariant for v in check_qrels(qrels)] == ["well_formed_id"]


# --- check_run_against_qrels ----------------------------------------------


def test_espaces_de_nommage_disjoints_signales() -> None:
    """Run en ECLI, qrels en ID DILA : intersection vide -> métriques 0 muettes."""
    run = Run(entries=(_entry("q1", "c1", "eli:D1", 1),))
    qrels = Qrels(
        judgments=(Judgment(query_id="q1", doc_id="dila:X1", chunk_id="c9", grade=3),)
    )
    violations = check_run_against_qrels(run, qrels)
    assert [v.invariant for v in violations] == ["shared_id_namespace"]


def test_intersection_non_vide_ne_signale_rien() -> None:
    run = Run(entries=(_entry("q1", "c1", "eli:D1", 1),))
    qrels = Qrels(
        judgments=(Judgment(query_id="q1", doc_id="eli:D1", chunk_id="c1", grade=3),)
    )
    assert check_run_against_qrels(run, qrels) == []


def test_requete_sans_recouvrement_de_cote_n_est_pas_une_incoherence() -> None:
    """Une requête présente d'un seul côté n'est pas un conflit de nommage."""
    run = Run(entries=(_entry("q1", "c1", "eli:D1", 1),))
    qrels = Qrels(
        judgments=(Judgment(query_id="q2", doc_id="dila:X1", chunk_id="c9", grade=3),)
    )
    assert check_run_against_qrels(run, qrels) == []


# --- InvariantError --------------------------------------------------------


def test_invariant_error_porte_toutes_les_violations() -> None:
    violations = [
        Violation(invariant="ranks_contiguous", query_id="q1", detail="…"),
        Violation(invariant="well_formed_id", query_id="q2", detail="…"),
    ]
    error = InvariantError(violations)
    assert error.violations == violations
    assert "2 invariant(s)" in str(error)
