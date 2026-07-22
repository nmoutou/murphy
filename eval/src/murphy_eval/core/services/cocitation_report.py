"""``summarize_pairs`` — la volumétrie d'un jeu de paires de co-citation.

E-P2-05 (reformulée par ADR-029) demande la strate 2 « volumétrie et méthode
documentées ». La *méthode* vit dans le code du miner et le README ; la
*volumétrie* est ce chiffre-ci, calculé sur le jeu extrait : combien de paires, la
ventilation par verbe, combien de documents distincts. Fonction **pure** (aucune
base) — elle s'applique aussi bien au retour du miner qu'à un fichier rechargé.

Ce résumé est **descriptif**, jamais une métrique de classement : conforme à
ADR-029, la strate 2 ne produit aucun grade ni score.
"""

from __future__ import annotations

from collections.abc import Sequence

from murphy_eval.core.models._base import Frozen
from murphy_eval.core.models.cocitation import CocitationPair


class CocitationSummary(Frozen):
    """La volumétrie d'un jeu de paires : totaux et ventilation par verbe."""

    pair_count: int
    document_count: int
    """Nombre de documents distincts apparaissant comme source ou cible."""
    pairs_by_verb: tuple[tuple[str, int], ...]
    """(verbe, nombre de paires), trié par verbe — reproductible."""


def summarize_pairs(pairs: Sequence[CocitationPair]) -> CocitationSummary:
    """Résume un jeu de paires. Trié par verbe pour un rapport déterministe."""
    by_verb: dict[str, int] = {}
    documents: set[str] = set()
    for pair in pairs:
        by_verb[pair.verb] = by_verb.get(pair.verb, 0) + 1
        documents.add(pair.source)
        documents.add(pair.target)
    return CocitationSummary(
        pair_count=len(pairs),
        document_count=len(documents),
        pairs_by_verb=tuple(sorted(by_verb.items())),
    )
