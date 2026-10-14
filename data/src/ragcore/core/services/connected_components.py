"""Les composantes connexes d'un graphe lu en flux, par union-find (ADR-034 §5).

La réduction transitive supprime ``a → c`` quand un chemin ``a → b → c`` existe ; deux
composantes connexes n'ont aucune arête commune, donc aucun chemin ne passe de l'une à
l'autre. Réduire composante par composante donne exactement la réduction du graphe
entier.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Component", "ConnectedComponents"]


@dataclass(frozen=True)
class Component:
    name: str
    """Son plus petit nœud : un nom stable, quel que soit l'ordre de lecture."""
    nodes: tuple[str, ...]
    relations: int
    """Les arêtes lues, doublons compris."""


class ConnectedComponents:
    """Une entrée par nœud, et la taille de chaque composante : jamais les arêtes.

    Union par taille et compression des chemins : chaque opération est quasi constante.
    """

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._nodes: dict[str, int] = {}
        """Par racine."""
        self._relations: dict[str, int] = {}
        """Par racine."""

    def add_edge(self, source: str, target: str) -> None:
        root = self._union(self._find(source), self._find(target))
        self._relations[root] += 1

    def components(self) -> list[Component]:
        """Triées par nom, pour un run reproductible. Vide l'union-find, qui n'a plus
        d'usage."""
        nodes_by_root: dict[str, list[str]] = {}
        for node in self._parent:
            nodes_by_root.setdefault(self._find(node), []).append(node)
        relations = self._relations
        self._parent, self._nodes, self._relations = {}, {}, {}
        found = [
            Component(min(nodes), tuple(sorted(nodes)), relations[root])
            for root, nodes in nodes_by_root.items()
        ]
        return sorted(found, key=lambda component: component.name)

    def _find(self, node: str) -> str:
        if node not in self._parent:
            self._parent[node] = node
            self._nodes[node] = 1
            self._relations[node] = 0
            return node
        root = node
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[node] != root:
            self._parent[node], node = root, self._parent[node]
        return root

    def _union(self, left: str, right: str) -> str:
        if left == right:
            return left
        if self._nodes[left] < self._nodes[right]:
            left, right = right, left
        self._parent[right] = left
        self._nodes[left] += self._nodes.pop(right)
        self._relations[left] += self._relations.pop(right)
        return left
