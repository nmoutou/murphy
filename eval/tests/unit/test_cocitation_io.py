from __future__ import annotations

from pathlib import Path

from murphy_eval.adapters.cocitation_io import dump_jsonl_pairs, load_jsonl_pairs
from murphy_eval.core.models.cocitation import CocitationPair

_PAIRS = (
    CocitationPair(
        source="eli:LEGIARTI000000000001",
        verb="cites",
        target="decision:JURITEXT000000000002",
    ),
    CocitationPair(
        source="eli:LEGIARTI000000000003",
        verb="succeeded_by",
        target="eli:LEGIARTI000000000004",
    ),
)


def test_dump_puis_load_redonne_les_memes_paires(tmp_path: Path) -> None:
    path = tmp_path / "pairs.jsonl"
    dump_jsonl_pairs(_PAIRS, path)
    assert load_jsonl_pairs(path) == _PAIRS


def test_dump_est_deterministe_byte_a_byte(tmp_path: Path) -> None:
    path_a = tmp_path / "a.jsonl"
    path_b = tmp_path / "b.jsonl"
    dump_jsonl_pairs(_PAIRS, path_a)
    dump_jsonl_pairs(_PAIRS, path_b)
    assert path_a.read_bytes() == path_b.read_bytes()


def test_ordre_recu_est_preserve(tmp_path: Path) -> None:
    """Le writer ne re-trie pas : l'ordre (déjà trié par le Cypher) est conservé."""
    path = tmp_path / "pairs.jsonl"
    reversed_pairs = tuple(reversed(_PAIRS))
    dump_jsonl_pairs(reversed_pairs, path)
    assert load_jsonl_pairs(path) == reversed_pairs


def test_jeu_vide_produit_un_fichier_vide(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    dump_jsonl_pairs((), path)
    assert path.read_text() == ""
    assert load_jsonl_pairs(path) == ()


def test_fixture_sur_disque_est_le_format_attendu() -> None:
    """La fixture versionnée documente le format ; ce test la tient à jour.

    Sans cette assertion, ``sane.pairs.jsonl`` dériverait en silence du modèle
    (c'est ce qui rendait le fichier orphelin sans valeur). Le round-trip par
    fichier réel prouve aussi la lecture des octets tels qu'ils sont commités.
    """
    path = Path(__file__).parent.parent / "data" / "sane.pairs.jsonl"
    assert load_jsonl_pairs(path) == _PAIRS
