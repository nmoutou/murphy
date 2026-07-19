from __future__ import annotations

from pathlib import Path

from murphy_eval.adapters.trec.projection import dump_jsonl_run, load_jsonl_run
from murphy_eval.core.models.run import Run, RunEntry


def _run() -> Run:
    return Run(
        entries=(
            RunEntry(
                query_id="q1",
                chunk_id="c1",
                doc_id="eli:LEGIARTI000000000001",
                rank=1,
                score=0.9,
                run_tag="baseline",
            ),
            RunEntry(
                query_id="q1",
                chunk_id="c2",
                doc_id="decision:JURITEXT000000000002",
                rank=2,
                score=0.7,
                run_tag="baseline",
            ),
        ),
        run_tag="baseline",
    )


def test_dump_puis_load_redonne_le_meme_run(tmp_path: Path) -> None:
    """Round-trip (ADR-008) : le writer est l'inverse exact du loader canonique.

    Note : ``run_tag`` au niveau ``Run`` n'est pas porté ligne à ligne, donc le
    ``Run`` rechargé le laisse à sa valeur par défaut ; on compare donc les
    entrées, seule donnée persistée en JSONL.
    """
    path = tmp_path / "run.jsonl"
    original = _run()
    dump_jsonl_run(original, path)
    reloaded = load_jsonl_run(path)
    assert reloaded.entries == original.entries


def test_dump_est_deterministe_byte_a_byte(tmp_path: Path) -> None:
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    dump_jsonl_run(_run(), path_a)
    dump_jsonl_run(_run(), path_b)
    assert path_a.read_bytes() == path_b.read_bytes()


def test_run_vide_produit_un_fichier_vide(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    dump_jsonl_run(Run(entries=()), path)
    assert path.read_text() == ""
    assert load_jsonl_run(path).entries == ()
