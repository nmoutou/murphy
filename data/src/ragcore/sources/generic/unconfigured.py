"""La cascade des balises absentes de la table (ADR-023) : rien ne disparaît, chaque
valeur a une destination.

- une valeur au format d'identifiant DILA, autre que le document lui-même → un lien
  heuristique (``HEURISTIC_KIND``) ;
- sinon → une métadonnée, sous sa clé chemin-complet (ADR-011).

Les balises connues n'arrivent jamais ici : la table tranche avant l'heuristique. Rien
n'est compté ici non plus : le site de parse déclare les signaux rangés dans
``UnconfiguredRouting``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any

from ragcore.core.links import HEURISTIC_KIND
from ragcore.core.models.identifiers import Identifier

from .occurrences import Occurrence
from .role_table import RoleTable
from .tree import Node, path_key, walk_with_path

__all__ = ["SourcedFacet", "UnconfiguredRouting", "route_unconfigured"]

SourcedFacet = tuple[Node, str]
"""Une facette et son fichier (vide s'il est inconnu)."""

_DILA_ID = re.compile(r"[A-Z]{8}[0-9]{12}\Z")
"""Le motif d'``IDENTIFIER_PATTERN``, testé sur la valeur, jamais sur le nom
d'attribut."""


@dataclass
class UnconfiguredRouting:
    """Ce que la cascade range, et ce qu'elle signale.

    ``occurrences`` et ``references`` sont ceux du document, que la cascade complète.
    Les signaux sont tenus par clé chemin-complet, jamais par nom de balise (ADR-024).
    """

    identifier: Identifier
    references: list[dict[str, Any]]
    occurrences: defaultdict[str, list[Occurrence]] = field(
        default_factory=lambda: defaultdict(list)
    )
    """Clé → ses valeurs, dans l'ordre de lecture."""
    tags: dict[str, str] = field(default_factory=dict)
    """Métadonnées non configurées : clé → fichier de la première facette qui la
    porte. Ce sont les clés que ``skip_unconfigured`` retire."""
    links: dict[str, str] = field(default_factory=dict)
    """Liens heuristiques : clé de leur balise → son fichier."""
    roots: dict[str, str] = field(default_factory=dict)
    """Racines XML non déclarées → le fichier qui les porte."""


@dataclass(frozen=True)
class _Origin:
    key: str
    tag: str
    source_file: str


def route_unconfigured(
    facets: list[SourcedFacet], table: RoleTable, routing: UnconfiguredRouting
) -> None:
    for facet, source_file in facets:
        if facet["tag"] not in table.roots:
            routing.roots.setdefault(facet["tag"], source_file)
        for node, path in walk_with_path(facet):
            if not table.knows(node["tag"]):
                origin = _Origin(path_key(path), node["tag"], source_file)
                _route_values(node, origin, routing)


def _route_values(node: Node, origin: _Origin, routing: UnconfiguredRouting) -> None:
    """Attributs, puis texte de feuille. Un nœud sans valeur n'a rien à ingérer."""
    for name, value in node["attrib"].items():
        text = str(value).strip()
        if text:
            attribute = replace(origin, key=f"{origin.key}_{name.lower()}")
            _route_value(routing, text, attribute)

    text = node["text"].strip()
    if text and not node["children"]:
        _route_value(routing, text, origin)


def _route_value(routing: UnconfiguredRouting, value: str, origin: _Origin) -> None:
    if _is_reference_value(value, routing.identifier):
        routing.references.append(
            {"kind": HEURISTIC_KIND, "id": value, "tag": origin.tag}
        )
        routing.links.setdefault(origin.key, origin.source_file)
        return
    routing.occurrences[origin.key].append(Occurrence(value, origin.source_file))
    routing.tags.setdefault(origin.key, origin.source_file)


def _is_reference_value(value: str, identifier: Identifier) -> bool:
    """Le format DILA, sauf le document lui-même : un ``cid`` qui porte son propre
    identifiant ne pointe vers rien."""
    return bool(_DILA_ID.fullmatch(value)) and value != identifier.raw
