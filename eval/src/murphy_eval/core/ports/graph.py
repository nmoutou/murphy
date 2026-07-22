"""Port du minage de co-citation : ``CocitationMiner``.

Le socle d'extraction de la strate 2 (B-07) lit le graphe Neo4j pour en tirer les
paires de documents liés. L'exprimer en ``Protocol`` — comme ``Searcher`` pour la
récupération (``ports/retrieval.py``) — permet de piloter la logique avec une
doublure en mémoire dans les tests unitaires, le vrai chemin réseau (Neo4j)
restant isolé dans l'adapter concret (``adapters/graph/neo4j_cocitation.py``) et
couvert par un test ``integration``.
"""

from __future__ import annotations

from typing import Protocol

from murphy_eval.core.models.cocitation import CocitationPair


class CocitationMiner(Protocol):
    def mine_pairs(self, *, owner_id: str) -> list[CocitationPair]: ...
