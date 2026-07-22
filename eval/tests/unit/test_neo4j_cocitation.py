"""Le miner piloté par une doublure en mémoire — sans réseau.

On teste ici le mapping ligne→``CocitationPair`` et le fail-fast sur clé manquante.
Le filtrage ``:Pending`` / auto-paire / ``owner_id`` vit dans le Cypher lui-même :
il est prouvé contre un vrai serveur dans ``tests/integration``.
"""

from __future__ import annotations

from typing import Any

import pytest

from murphy_eval.adapters.graph.neo4j_cocitation import (
    Neo4jCocitationMiner,
    _record_to_pair,
)
from murphy_eval.core.models.cocitation import CocitationPair


class _FakeRecord:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def data(self) -> dict[str, object]:
        return self._data


class _FakeSession:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.captured_params: dict[str, Any] = {}

    def run(self, _query: str, **params: Any) -> list[_FakeRecord]:
        self.captured_params = params
        return [_FakeRecord(row) for row in self._rows]

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _FakeDriver:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session
        self.closed = False

    def session(self) -> _FakeSession:
        return self._session

    def close(self) -> None:
        self.closed = True


def _miner_with(
    rows: list[dict[str, object]],
) -> tuple[Neo4jCocitationMiner, _FakeSession]:
    session = _FakeSession(rows)
    miner = Neo4jCocitationMiner.__new__(Neo4jCocitationMiner)
    miner._driver = _FakeDriver(session)  # type: ignore[attr-defined]
    return miner, session


def test_mine_pairs_mappe_les_lignes_en_paires() -> None:
    rows: list[dict[str, object]] = [
        {"source": "eli:A", "verb": "cites", "target": "decision:B"},
        {"source": "eli:C", "verb": "succeeded_by", "target": "eli:D"},
    ]
    miner, _ = _miner_with(rows)
    pairs = miner.mine_pairs(owner_id="system")
    assert pairs == [
        CocitationPair(source="eli:A", verb="cites", target="decision:B"),
        CocitationPair(source="eli:C", verb="succeeded_by", target="eli:D"),
    ]


def test_mine_pairs_passe_owner_id_en_parametre() -> None:
    miner, session = _miner_with([])
    miner.mine_pairs(owner_id="tenant-x")
    assert session.captured_params == {"owner_id": "tenant-x"}


def test_le_miner_ferme_sa_connexion_en_sortie_de_contexte() -> None:
    """``with`` ferme le driver — y compris si le bloc lève (C-05)."""
    miner, _ = _miner_with([])
    driver = miner._driver  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError), miner:
        raise RuntimeError("le bloc échoue")

    assert driver.closed


def test_record_to_pair_fail_fast_sur_valeur_nulle() -> None:
    """Le cas réel : Neo4j rend toujours les clés, une prop absente vaut ``None``.

    Un dict *tronqué* ne prouverait rien — le driver n'en produit jamais. Sans ce
    garde-fou, ``str(None)`` fabriquerait l'identifiant ``"None"``.
    """
    with pytest.raises(ValueError, match="incohérent"):
        _record_to_pair({"source": "eli:A", "verb": "cites", "target": None})


def test_record_to_pair_nomme_tous_les_champs_manquants() -> None:
    with pytest.raises(ValueError, match="verb, target"):
        _record_to_pair({"source": "eli:A", "verb": None, "target": None})
