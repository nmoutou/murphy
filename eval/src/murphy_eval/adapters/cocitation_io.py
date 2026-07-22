"""Persistance des paires de co-citation — JSONL dédié, immuable.

**Pas le format qrels ADR-008 — délibérément.** ADR-029 écarte explicitement le
libellé « qrels » pour la strate 2 : réutiliser ce format entretiendrait la
confusion sortie-machine / vérité-terrain que tout l'ADR combat. Un jeu de paires
est un *diagnostic* (précision-seulement), pas un étalon de classement — d'où un
schéma propre, hors du paquet ``trec/``.

Writer/loader calqués sur ``adapters/trec/projection.py:dump_jsonl_run`` : une
ligne ``CocitationPair`` par paire, ``model_dump`` fige l'ordre des clés, l'ordre
des lignes vient déjà trié du Cypher (``ORDER BY source, verb, target``). Deux
``dump`` du même jeu produisent des **octets identiques** ; ``dump`` puis ``load``
redonne les mêmes paires (round-trip).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from murphy_eval.core.models.cocitation import CocitationPair


def dump_jsonl_pairs(pairs: Iterable[CocitationPair], path: Path) -> None:
    """Écrit les paires en JSONL immuable, une ``CocitationPair`` par ligne.

    L'ordre reçu est préservé tel quel (le minage le rend déjà trié) : le fichier
    est donc reproductible bit-à-bit. ``ensure_ascii=False`` garde les identifiants
    lisibles ; ``separators`` compacte sans espace superflu.

    ``encoding="utf-8"`` est **explicite et nécessaire** : sans lui, ``write_text``
    suit la locale du poste, et « reproductible bit-à-bit » ne vaudrait que sur une
    machine donnée — d'autant que ``ensure_ascii=False`` laisse passer du non-ASCII.
    """
    lines = (
        json.dumps(pair.model_dump(), ensure_ascii=False, separators=(",", ":"))
        for pair in pairs
    )
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def load_jsonl_pairs(path: Path) -> tuple[CocitationPair, ...]:
    """Recharge un jeu de paires JSONL, une ``CocitationPair`` par ligne non vide."""
    return tuple(
        CocitationPair.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
