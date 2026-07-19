"""Le port ``Retriever`` — le contrat d'adapter d'ADR-016, côté domaine.

ADR-016 pose un contrat unique : une config de récupération, quelle que soit sa
mécanique interne (dense, graphe, hybride), expose `requête → liste ordonnée
d'IDs canoniques (+ scores)`. Ce ``Protocol`` *est* ce contrat, typé.

Même discipline que ``ports/scorer.py`` : le domaine (et demain l'orchestrateur
de sweep, B-13) dépend de l'interface, jamais de l'adapter concret
(``adapters/retrieval/baseline.py``). B-13 pilotera plusieurs ``Retriever`` —
un par point de l'espace ``R`` — sur des collections produites par différents
``W``, sans rien connaître de Qdrant ni de TEI.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from murphy_eval.core.models.run import Run
from murphy_eval.core.models.runtime import RuntimeConfig, Topic


class Retriever(Protocol):
    def retrieve(self, topics: Sequence[Topic], config: RuntimeConfig) -> Run: ...
