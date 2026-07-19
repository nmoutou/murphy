"""Ports des collaborateurs de la récupération : ``Embedder`` et ``Searcher``.

``BaselineRetriever`` (l'implémentation du port ``Retriever``, ADR-016) se
compose de deux étages substituables : embarquer le texte, puis chercher les
plus proches voisins. Les exprimer en ``Protocol`` permet de piloter la
baseline avec des doublures en mémoire dans les tests unitaires — le vrai
chemin réseau (TEI, Qdrant) reste isolé dans les adapters concrets et couvert
par un test ``integration``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from murphy_eval.adapters.retrieval.hits import Hit


class Embedder(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...


class Searcher(Protocol):
    def search(self, vector: Sequence[float], *, top_k: int) -> list[Hit]: ...
