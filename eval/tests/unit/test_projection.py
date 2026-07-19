from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from murphy_eval.adapters.trec.projection import (
    load_jsonl_qrels,
    load_jsonl_run,
    load_trec_qrels,
    load_trec_run,
)
from murphy_eval.core.models.judgment import Judgment, Qrels
from murphy_eval.core.models.run import Run, RunEntry


def test_load_jsonl_qrels(tmp_path: Path) -> None:
    path = tmp_path / "qrels.jsonl"
    path.write_text(
        '{"query_id": "q1", "doc_id": "D1", "chunk_id": "c1", "grade": 3}\n'
        '{"query_id": "q1", "doc_id": "D2", "chunk_id": "c2", "grade": 1}\n'
    )
    qrels = load_jsonl_qrels(path)
    assert qrels == Qrels(
        judgments=(
            Judgment(query_id="q1", doc_id="D1", chunk_id="c1", grade=3),
            Judgment(query_id="q1", doc_id="D2", chunk_id="c2", grade=1),
        )
    )


def test_load_jsonl_qrels_grade_hors_plage_echoue(tmp_path: Path) -> None:
    path = tmp_path / "qrels.jsonl"
    path.write_text(
        '{"query_id": "q1", "doc_id": "D1", "chunk_id": "c1", "grade": 4}\n'
    )
    with pytest.raises(ValidationError):
        load_jsonl_qrels(path)


def test_load_jsonl_run(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        '{"query_id": "q1", "chunk_id": "c1", "doc_id": "D1", "rank": 1, "score": 0.9}\n'
    )
    run = load_jsonl_run(path)
    assert run == Run(
        entries=(
            RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=1, score=0.9),
        )
    )


def test_load_trec_qrels(tmp_path: Path) -> None:
    path = tmp_path / "qrels.trec"
    path.write_text("q1 0 c1 3\nq1 0 c2 1\n")
    qrels = load_trec_qrels(path)
    grades = {j.chunk_id: j.grade for j in qrels.judgments}
    assert grades == {"c1": 3, "c2": 1}


def test_load_trec_run_utilise_le_resolveur_pour_doc_id(tmp_path: Path) -> None:
    path = tmp_path / "run.trec"
    path.write_text("q1 Q0 c1 1 0.9 baseline\n")
    run = load_trec_run(path, resolve_doc_id=lambda chunk_id: f"doc-of-{chunk_id}")
    assert run.entries[0].doc_id == "doc-of-c1"
    assert run.entries[0].rank == 1
    assert run.entries[0].score == 0.9
    assert run.entries[0].run_tag == "baseline"


def test_load_trec_qrels_ignore_les_lignes_vides(tmp_path: Path) -> None:
    path = tmp_path / "qrels.trec"
    path.write_text("q1 0 c1 3\n\n\nq1 0 c2 1\n")
    qrels = load_trec_qrels(path)
    assert len(qrels.judgments) == 2


def test_jsonl_et_trec_produisent_des_modeles_compatibles(tmp_path: Path) -> None:
    """Même contenu logique, deux formats : les champs porteurs pour le
    scorer (query_id, chunk_id, grade) concordent.
    """
    jsonl_path = tmp_path / "q.jsonl"
    jsonl_path.write_text(
        '{"query_id": "q1", "doc_id": "D1", "chunk_id": "c1", "grade": 2}\n'
    )
    trec_path = tmp_path / "q.trec"
    trec_path.write_text("q1 0 c1 2\n")

    from_jsonl = load_jsonl_qrels(jsonl_path).judgments[0]
    from_trec = load_trec_qrels(trec_path).judgments[0]
    assert from_jsonl.query_id == from_trec.query_id
    assert from_jsonl.chunk_id == from_trec.chunk_id
    assert from_jsonl.grade == from_trec.grade
