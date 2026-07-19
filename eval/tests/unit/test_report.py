from __future__ import annotations

from murphy_eval.core.models.gains import linear_gain
from murphy_eval.core.models.judgment import Judgment, Qrels
from murphy_eval.core.models.run import Run, RunEntry
from murphy_eval.core.services.report import score


def _qrels() -> Qrels:
    return Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="D1", chunk_id="c1", grade=3),
            Judgment(query_id="q2", doc_id="D2", chunk_id="c2", grade=2),
        )
    )


def _run() -> Run:
    return Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=1, score=1.0),
            RunEntry(query_id="q2", chunk_id="c2", doc_id="D2", rank=1, score=1.0),
        )
    )


def test_report_porte_la_table_complete_par_requete() -> None:
    report = score(_qrels(), _run())
    assert {q.query_id for q in report.per_query} == {"q1", "q2"}


def test_report_ventile_par_type_action() -> None:
    report = score(
        _qrels(), _run(), action_types={"q1": "known_item", "q2": "graph_hop"}
    )
    types = dict(report.by_action_type)
    assert set(types.keys()) == {"known_item", "graph_hop"}
    assert types["known_item"].query_count == 1


def test_report_sans_action_types_ventilation_vide() -> None:
    report = score(_qrels(), _run())
    assert report.by_action_type == ()


def test_report_moyenne_ndcg_exclut_les_requetes_r_zero() -> None:
    qrels = Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="D1", chunk_id="c1", grade=3),
            Judgment(query_id="q2", doc_id="D2", chunk_id="c2", grade=0),
        )
    )
    run = Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=1, score=1.0),
            RunEntry(query_id="q2", chunk_id="c2", doc_id="D2", rank=1, score=1.0),
        )
    )
    report = score(qrels, run)
    # q1 a nDCG@R=1.0 (ranking parfait), q2 a R=0 -> None, exclu de la moyenne.
    assert report.aggregate.ndcg_at_r_count == 1
    assert report.aggregate.ndcg_at_r_mean == 1.0


def test_report_gain_injectable_change_le_ndcg() -> None:
    qrels = Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="a", chunk_id="a#0", grade=3),
            Judgment(query_id="q1", doc_id="b", chunk_id="b#0", grade=1),
        )
    )
    run = Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="b#0", doc_id="b", rank=1, score=2.0),
            RunEntry(query_id="q1", chunk_id="a#0", doc_id="a", rank=2, score=1.0),
        )
    )
    report_exp = score(qrels, run)
    report_lin = score(qrels, run, gain=linear_gain)
    assert report_exp.per_query[0].ndcg_at_r != report_lin.per_query[0].ndcg_at_r


def test_report_requetes_sans_recoupement_qrels_run() -> None:
    """Une requête présente dans les qrels mais absente du run (rien
    retrouvé) doit apparaître dans le rapport avec des métriques à zéro,
    jamais faire planter le scoring.
    """
    qrels = Qrels(
        judgments=(Judgment(query_id="q1", doc_id="D1", chunk_id="c1", grade=2),)
    )
    run = Run(entries=())
    report = score(qrels, run)
    assert len(report.per_query) == 1
    assert report.per_query[0].ndcg_at_r == 0.0
