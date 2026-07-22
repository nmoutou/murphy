"""La CLI de co-citation, pilotée par une doublure de miner — sans réseau.

Le port ``CocitationMiner`` est fait pour ça : on injecte une doublure et on
vérifie le **câblage** (les bons artefacts, au bon endroit, avec le bon contenu),
le vrai chemin Neo4j étant prouvé par ``tests/integration``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from murphy_eval.adapters.cocitation_io import load_jsonl_pairs
from murphy_eval.cli.cocitation import (
    PAIRS_FILENAME,
    SUMMARY_FILENAME,
    _parse_args,
    main,
    run,
)
from murphy_eval.core.models.cocitation import CocitationPair

_PAIRS = [
    CocitationPair(source="eli:A", verb="cites", target="decision:B"),
    CocitationPair(source="eli:A", verb="succeeded_by", target="eli:C"),
    CocitationPair(source="eli:C", verb="cites", target="decision:B"),
]


class _FakeMiner:
    """Rend des paires figées et retient l'``owner_id`` reçu."""

    def __init__(self, pairs: list[CocitationPair] | None = None) -> None:
        self._pairs = _PAIRS if pairs is None else pairs
        self.owner_id: str | None = None
        self.closed = False

    def mine_pairs(self, *, owner_id: str) -> list[CocitationPair]:
        self.owner_id = owner_id
        return self._pairs

    def close(self) -> None:
        self.closed = True


class _BrokenMiner:
    """Le graphe incohérent : ce que lève le fail-fast de ``_record_to_pair``."""

    def __init__(self) -> None:
        self.closed = False

    def mine_pairs(self, *, owner_id: str) -> list[CocitationPair]:
        raise ValueError("Ligne Neo4j sans target — graphe incohérent")

    def close(self) -> None:
        self.closed = True


def test_run_ecrit_les_deux_artefacts(tmp_path: Path) -> None:
    summary = run(_FakeMiner(), owner_id="system", out_dir=tmp_path)

    assert (tmp_path / PAIRS_FILENAME).exists()
    assert (tmp_path / SUMMARY_FILENAME).exists()
    assert summary.pair_count == 3


def test_pairs_jsonl_se_recharge_a_l_identique(tmp_path: Path) -> None:
    """L'artefact est relisible par le loader du projet — pas juste du texte."""
    run(_FakeMiner(), owner_id="system", out_dir=tmp_path)
    assert load_jsonl_pairs(tmp_path / PAIRS_FILENAME) == tuple(_PAIRS)


def test_summary_json_porte_la_volumetrie(tmp_path: Path) -> None:
    """C'est ce fichier qui fait la preuve d'E-P2-05 : il doit être exact."""
    run(_FakeMiner(), owner_id="system", out_dir=tmp_path)

    payload = json.loads((tmp_path / SUMMARY_FILENAME).read_text(encoding="utf-8"))
    assert payload["pair_count"] == 3
    assert payload["document_count"] == 3  # eli:A, eli:C, decision:B
    assert payload["pairs_by_verb"] == [["cites", 2], ["succeeded_by", 1]]


def test_run_cree_le_repertoire_absent(tmp_path: Path) -> None:
    out_dir = tmp_path / "pas" / "encore" / "la"
    run(_FakeMiner(), owner_id="system", out_dir=out_dir)
    assert (out_dir / PAIRS_FILENAME).exists()


def test_run_est_reproductible_byte_a_byte(tmp_path: Path) -> None:
    """Rejouer la commande sur le même graphe ne doit produire aucun diff git."""
    first, second = tmp_path / "a", tmp_path / "b"
    run(_FakeMiner(), owner_id="system", out_dir=first)
    run(_FakeMiner(), owner_id="system", out_dir=second)

    for name in (PAIRS_FILENAME, SUMMARY_FILENAME):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_jeu_vide_reste_un_artefact_valide(tmp_path: Path) -> None:
    summary = run(_FakeMiner(pairs=[]), owner_id="system", out_dir=tmp_path)
    assert summary.pair_count == 0
    assert (tmp_path / PAIRS_FILENAME).read_text(encoding="utf-8") == ""


def test_owner_id_est_transmis_au_miner(tmp_path: Path) -> None:
    miner = _FakeMiner()
    run(miner, owner_id="tenant-x", out_dir=tmp_path)
    assert miner.owner_id == "tenant-x"


def test_defauts_de_la_ligne_de_commande() -> None:
    """``--owner-id`` non fourni vaut ``None`` : c'est ``main`` qui lit les settings.

    Le tenant ne doit **pas** être codé en dur ici. Une version antérieure figeait
    ``"system"`` alors que l'ingestion écrit ``OWNER_ID`` (``"default"``) : la
    commande minait un tenant inexistant et rendait un artefact vide en code 0.
    """
    args = _parse_args([])
    assert args.owner_id is None
    assert args.out_dir.is_absolute()  # jamais relatif au CWD
    assert args.out_dir.parts[-2:] == ("artifacts", "cocitation")


def test_main_succes_rend_zero_et_ferme_le_miner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    miner = _FakeMiner()
    monkeypatch.setattr("murphy_eval.cli.cocitation.build_miner", lambda: miner)

    code = main(["--out-dir", str(tmp_path), "--owner-id", "default"])

    captured = capsys.readouterr()
    assert code == 0
    assert miner.closed
    assert "3 paires" in captured.out
    assert "default" in captured.out  # le tenant est affiché, sinon indiagnosticable


def test_main_sans_owner_id_lit_les_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le tenant vient du ``.env.dev`` partagé avec l'ingestion, pas d'un littéral.

    C'est le correctif du défaut mesuré contre le vrai graphe : ``"system"`` codé
    en dur ne matchait aucun nœud (l'ingestion écrit ``"default"``).
    """
    miner = _FakeMiner()
    monkeypatch.setattr("murphy_eval.cli.cocitation.build_miner", lambda: miner)
    monkeypatch.setattr(
        "murphy_eval.cli.cocitation.get_eval_infra_settings",
        lambda: SimpleNamespace(owner_id="depuis-les-settings"),
    )

    main(["--out-dir", str(tmp_path)])

    assert miner.owner_id == "depuis-les-settings"


def test_main_jeu_vide_avertit_sur_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Un artefact vide reste un succès (code 0) mais ne doit jamais être muet."""
    monkeypatch.setattr(
        "murphy_eval.cli.cocitation.build_miner", lambda: _FakeMiner(pairs=[])
    )

    code = main(["--out-dir", str(tmp_path), "--owner-id", "tenant-inexistant"])

    captured = capsys.readouterr()
    assert code == 0
    assert "Aucune paire minée" in captured.err


def test_main_graphe_incoherent_rend_un_sans_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Un graphe hors contrat est une condition d'exploitation, pas un crash."""
    miner = _BrokenMiner()
    monkeypatch.setattr("murphy_eval.cli.cocitation.build_miner", lambda: miner)

    code = main(["--out-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == 1
    assert "incohérent" in captured.err
    assert "Traceback" not in captured.err
    assert miner.closed  # la connexion est fermée même en échec


def test_main_connexion_impossible_rend_un(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Settings absents ou Neo4j injoignable : message clair, pas de traceback."""

    def _boom() -> None:
        raise OSError("NEO4J_URI manquant")

    monkeypatch.setattr("murphy_eval.cli.cocitation.build_miner", _boom)

    code = main([])

    captured = capsys.readouterr()
    assert code == 1
    assert "NEO4J_URI manquant" in captured.err
    assert "Traceback" not in captured.err
