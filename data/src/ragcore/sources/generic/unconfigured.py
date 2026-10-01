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

Rien ne disparaît, et rien n'est compté ici : le SIGNAL (balises et racines
non-configurées) sort dans ``UnconfiguredRouting``, et c'est le site de parse — qui tient
la télémétrie — qui le déclare. Pureté du parser préservée.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ragcore.core.links import HEURISTIC_KIND
from ragcore.core.models.identifiers import Identifier

from .role_table import RoleTable
from .tree import Node, path_key, walk_with_path

__all__ = ["UnconfiguredRouting", "route_unconfigured"]

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
    n'en fabrique pas d'autres.
    """

    identifier: Identifier
    metadata: dict[str, Any]
    references: list[dict[str, Any]]
    tags: list[str] = field(default_factory=list)
    """Les balises non-configurées rencontrées : absentes de la table, ou sans
    renommage."""
    keys: list[str] = field(default_factory=list)
    """Les clés de métadonnées que la cascade a ajoutées."""
    roots: list[str] = field(default_factory=list)
    """Les racines XML que la source ne déclare pas."""


def route_unconfigured(
    facets: list[Node], table: RoleTable, routing: UnconfiguredRouting
) -> None:
    """Route chaque balise NON-CONFIGURÉE vers sa porte."""
    for facet in facets:
        if facet["tag"] not in table.roots and facet["tag"] not in routing.roots:
            routing.roots.append(facet["tag"])
        for node, path in walk_with_path(facet):
            if table.knows(node["tag"]):
                continue
            if node["tag"] not in routing.tags:
                routing.tags.append(node["tag"])
            _route_values(node, path_key(path), routing)


def _route_values(node: Node, key_base: str, routing: UnconfiguredRouting) -> None:
    """Les VALEURS d'un nœud non-configuré : attributs, puis texte de feuille."""
    for name, value in node["attrib"].items():
        text = str(value).strip()
        if text:
            _route_value(routing, text, f"{key_base}_{name.lower()}", node["tag"])

    text = node["text"].strip()
    if text and not node["children"]:
        _route_value(routing, text, key_base, node["tag"])


def _route_value(routing: UnconfiguredRouting, value: str, key: str, tag: str) -> None:
    """Une valeur passe la porte liens si elle POINTE, la porte metadata sinon."""
    if _is_reference_value(value, routing.identifier):
        routing.references.append({"kind": HEURISTIC_KIND, "id": value, "tag": tag})
        return
    if key not in routing.metadata:
        routing.metadata[key] = value
        routing.keys.append(key)


def _is_reference_value(value: str, identifier: Identifier) -> bool:
    """Règles 3-4 de la cascade : la forme DILA, sauf soi-même.

    La comparaison à l'identité du document courant est STRUCTURELLE — pas une liste
    noire : un ``cid`` qui porte l'identifiant du document décrit le document, il ne
    pointe vers rien.
    """
    return bool(_DILA_ID.fullmatch(value)) and value != identifier.raw
