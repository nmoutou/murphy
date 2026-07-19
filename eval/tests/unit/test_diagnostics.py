from __future__ import annotations

from murphy_eval.core.models.aggregated import DocQrels, DocRun
from murphy_eval.core.services.diagnostics import (
    doc_recall_at_r,
    map_and_doc_mrr,
    r_precision,
    recall_at_2r,
)


def test_r_precision_r_zero_vaut_zero() -> None:
    assert r_precision({}, []) == 0.0
    assert r_precision({"a": 0}, ["a"]) == 0.0


def test_recall_at_2r_r_zero_vaut_zero() -> None:
    assert recall_at_2r({"a": 0}, ["a"]) == 0.0


def test_doc_recall_at_r_r_zero_vaut_zero() -> None:
    assert doc_recall_at_r({"a": 0}, ["a"]) == 0.0


def test_r_precision_aucun_pertinent_dans_le_top_r() -> None:
    grades = {"a": 2, "b": 1}
    ranked = ["non_pertinent_1", "non_pertinent_2", "a", "b"]
    assert r_precision(grades, ranked) == 0.0


def test_recall_at_2r_capture_au_dela_de_r() -> None:
    """Un pertinent en position R+1 est manqué par R-Precision mais
    capturé par Recall@2R.
    """
    grades = {"a": 2, "b": 1}  # R=2
    ranked = ["non_pertinent", "a", "b"]  # b arrive en position 3 = R+1
    assert r_precision(grades, ranked) == 0.5  # seul "a" dans le top-2
    assert recall_at_2r(grades, ranked) == 1.0  # top-4 capture les deux


def test_diagnostics_bornees_a_1_malgre_un_doublon_dans_le_run() -> None:
    """Les métriques à coupe (R-Precision, Recall@2R, Doc-Recall@R) restent
    dans [0, 1] même si un ``doc_id`` apparaît en double dans le classement :
    un même document ne compte jamais deux fois comme un hit distinct.
    """
    grades = {"a": 1}  # R = 1
    assert r_precision(grades, ["a", "a"]) == 1.0
    assert recall_at_2r(grades, ["a", "a"]) == 1.0
    assert doc_recall_at_r(grades, ["a", "a"]) == 1.0


def test_map_and_doc_mrr_requete_absente_du_run_vaut_zero() -> None:
    doc_qrels = {"q1": DocQrels(query_id="q1", doc_grades=(("a", 1),))}
    doc_runs: dict[str, DocRun] = {}
    result = map_and_doc_mrr(doc_qrels, doc_runs)
    assert result["q1"] == (0.0, 0.0)


def test_map_and_doc_mrr_ensemble_vide() -> None:
    assert map_and_doc_mrr({}, {}) == {}


def test_map_and_doc_mrr_couvre_toutes_les_requetes() -> None:
    doc_qrels = {
        "q1": DocQrels(query_id="q1", doc_grades=(("a", 1),)),
        "q2": DocQrels(query_id="q2", doc_grades=(("b", 1),)),
    }
    doc_runs = {
        "q1": DocRun(query_id="q1", doc_ranks=(("a", 1),)),
        "q2": DocRun(query_id="q2", doc_ranks=(("b", 1),)),
    }
    result = map_and_doc_mrr(doc_qrels, doc_runs)
    assert set(result.keys()) == {"q1", "q2"}
    assert result["q1"] == (1.0, 1.0)
    assert result["q2"] == (1.0, 1.0)
