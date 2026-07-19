from __future__ import annotations

from murphy_eval.core.models.judgment import Judgment, Qrels
from murphy_eval.core.models.run import Run, RunEntry
from murphy_eval.core.services.aggregation import aggregate_qrels, aggregate_run


def test_aggregate_qrels_prend_le_max_par_document() -> None:
    qrels = Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="D1", chunk_id="c1", grade=1),
            Judgment(query_id="q1", doc_id="D1", chunk_id="c2", grade=3),
            Judgment(query_id="q1", doc_id="D1", chunk_id="c3", grade=2),
        )
    )
    result = aggregate_qrels(qrels)
    assert result["q1"].as_dict() == {"D1": 3}


def test_aggregate_qrels_groupe_par_requete() -> None:
    qrels = Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="D1", chunk_id="c1", grade=1),
            Judgment(query_id="q2", doc_id="D2", chunk_id="c2", grade=2),
        )
    )
    result = aggregate_qrels(qrels)
    assert set(result.keys()) == {"q1", "q2"}
    assert result["q1"].as_dict() == {"D1": 1}
    assert result["q2"].as_dict() == {"D2": 2}


def test_aggregate_run_ignore_les_chunks_suivants_du_meme_document() -> None:
    run = Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=1, score=3.0),
            RunEntry(query_id="q1", chunk_id="c2", doc_id="D1", rank=2, score=2.0),
            RunEntry(query_id="q1", chunk_id="c3", doc_id="D2", rank=3, score=1.0),
        )
    )
    result = aggregate_run(run)
    # D1 apparaît une seule fois (son premier chunk, rang 1) ; D2 ensuite.
    assert result["q1"].ranked_doc_ids() == ["D1", "D2"]


def test_aggregate_run_densifie_les_rangs() -> None:
    """Des rangs d'entrée non contigus (car des chunks ont été consommés par
    un document déjà vu) redeviennent 1..n contigus en sortie.
    """
    run = Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=1, score=5.0),
            RunEntry(query_id="q1", chunk_id="c2", doc_id="D1", rank=2, score=4.0),
            RunEntry(query_id="q1", chunk_id="c3", doc_id="D2", rank=3, score=3.0),
        )
    )
    result = aggregate_run(run)
    assert result["q1"].doc_ranks == (("D1", 1), ("D2", 2))


def test_aggregate_run_independant_de_l_ordre_d_arrivee_des_lignes() -> None:
    """Le résultat ne dépend que du rang porté par chaque ligne, jamais de
    l'ordre dans lequel les lignes ont été ajoutées à ``Run.entries``.
    """
    en_ordre = Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=1, score=2.0),
            RunEntry(query_id="q1", chunk_id="c2", doc_id="D2", rank=2, score=1.0),
        )
    )
    inverse = Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="c2", doc_id="D2", rank=2, score=1.0),
            RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=1, score=2.0),
        )
    )
    assert aggregate_run(en_ordre) == aggregate_run(inverse)


def test_aggregate_qrels_vide() -> None:
    assert aggregate_qrels(Qrels(judgments=())) == {}


def test_aggregate_run_vide() -> None:
    assert aggregate_run(Run(entries=())) == {}
