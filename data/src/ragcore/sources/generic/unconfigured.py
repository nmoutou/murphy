"""La cascade des trois portes : ce que la table de rôles ne sait pas ranger.

C'est l'un des deux cas de balise NON-CONFIGURÉE (ADR-047) : la balise est absente de la
table. L'autre, une balise connue sans renommage, est traité par ``metadata.py`` et
alimente le même ``UnconfiguredRouting``.

Il n'y a plus d'« unknown » : une balise que la table ne connaît pas est une donnée dont
on n'a pas encore promu le nom, et elle a une DESTINATION —

- sa valeur a la forme d'un identifiant DILA et n'est pas le document lui-même (règle
  auto-id) → **porte liens** : une référence ``HEURISTIC_KIND``, que ``core/links``
  traduira en arête ``references`` ;
- sinon → **porte metadata**, sous sa clé chemin-complet (injective, ADR-022 §3).

Les balises CONNUES n'arrivent jamais ici (``knows()`` les écarte) : c'est la cascade du
cadrage, où la table tranche AVANT l'heuristique — ``VERSION`` et les titres sont
déclarés, ils ne peuvent pas devenir de faux liens.

Rien ne disparaît, et rien n'est compté ici : le SIGNAL (métadonnées, liens et racines
non-configurés) sort dans ``UnconfiguredRouting``, et c'est le site de parse — qui tient
la télémétrie — qui le déclare. Pureté du parser préservée.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

from ragcore.core.links import HEURISTIC_KIND
from ragcore.core.models.identifiers import Identifier

from .role_table import RoleTable
from .tree import Node, path_key, walk_with_path

__all__ = ["SourcedFacet", "UnconfiguredRouting", "route_unconfigured"]

SourcedFacet = tuple[Node, str]
"""Une facette du document et le fichier d'où elle vient (vide s'il est inconnu)."""

_DILA_ID = re.compile(r"[A-Z]{8}[0-9]{12}\Z")
"""La forme d'un identifiant DILA (``LEGIARTI000006219120``) — le même motif que
``IDENTIFIER_PATTERN`` du modèle ``Identifier``.

C'est le déclencheur de la règle 4 de la cascade : du duck-typing sur
la VALEUR, jamais sur le nom d'attribut. Mesuré sur le corpus : ``origine="LEGI"`` ne
matche pas (à raison), et les porteurs légitimes hors liens (``VERSION``, ``TITRE_TM``,
l'auto-``cid`` de ``TEXTE``) sont tous des balises CONNUES de la table — ils n'arrivent
jamais jusqu'à l'heuristique, qui ne voit que le vocabulaire non-configuré.
"""


@dataclass
class UnconfiguredRouting:
    """Ce que la cascade range, et ce qu'elle signale.

    ``metadata`` et ``references`` sont ceux du document : la cascade les COMPLÈTE, elle
    n'en fabrique pas d'autres. Les signaux sont tenus par CLÉ CHEMIN-COMPLET (ADR-048),
    jamais par nom de balise : c'est la clé qui dit où est la donnée.
    """

    identifier: Identifier
    metadata: dict[str, Any]
    references: list[dict[str, Any]]
    tags: dict[str, str] = field(default_factory=dict)
    """Les métadonnées non-configurées ajoutées (absentes de la table, ou sans
    renommage) : leur clé → le fichier de la première facette qui les porte. Ce sont
    aussi les clés que le curseur ``skip_unconfigured`` retire."""
    links: dict[str, str] = field(default_factory=dict)
    """Les liens heuristiques (porte liens) : la clé de leur balise → son fichier."""
    roots: dict[str, str] = field(default_factory=dict)
    """Les racines XML que la source ne déclare pas → le fichier qui les porte."""


@dataclass(frozen=True)
class _Origin:
    """D'où vient une valeur : sa clé chemin-complet, sa balise, son fichier."""

    key: str
    tag: str
    source_file: str


def route_unconfigured(
    facets: list[SourcedFacet], table: RoleTable, routing: UnconfiguredRouting
) -> None:
    """Route chaque balise NON-CONFIGURÉE vers sa porte."""
    for facet, source_file in facets:
        if facet["tag"] not in table.roots:
            routing.roots.setdefault(facet["tag"], source_file)
        for node, path in walk_with_path(facet):
            if not table.knows(node["tag"]):
                _route_values(
                    node, _Origin(path_key(path), node["tag"], source_file), routing
                )


def _route_values(node: Node, origin: _Origin, routing: UnconfiguredRouting) -> None:
    """Les VALEURS d'un nœud non-configuré : attributs, puis texte de feuille. Un nœud
    sans valeur ne laisse aucune trace : il n'a rien à ingérer."""
    for name, value in node["attrib"].items():
        text = str(value).strip()
        if text:
            attribute = replace(origin, key=f"{origin.key}_{name.lower()}")
            _route_value(routing, text, attribute)

    text = node["text"].strip()
    if text and not node["children"]:
        _route_value(routing, text, origin)


def _route_value(routing: UnconfiguredRouting, value: str, origin: _Origin) -> None:
    """Une valeur passe la porte liens si elle POINTE, la porte metadata sinon."""
    if _is_reference_value(value, routing.identifier):
        routing.references.append(
            {"kind": HEURISTIC_KIND, "id": value, "tag": origin.tag}
        )
        routing.links.setdefault(origin.key, origin.source_file)
        return
    if origin.key not in routing.metadata:
        routing.metadata[origin.key] = value
        routing.tags.setdefault(origin.key, origin.source_file)


def _is_reference_value(value: str, identifier: Identifier) -> bool:
    """Règles 3-4 de la cascade : la forme DILA, sauf soi-même.

    La comparaison à l'identité du document courant est STRUCTURELLE — pas une liste
    noire : un ``cid`` qui porte l'identifiant du document décrit le document, il ne
    pointe vers rien.
    """
    return bool(_DILA_ID.fullmatch(value)) and value != identifier.raw
