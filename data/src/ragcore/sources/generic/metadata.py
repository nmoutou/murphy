"""Les métadonnées des conteneurs ``<META>``, canonicalisées par la table.

Ni le contenu ni les liens n'y sont : ils ont leur place, et la dupliquer ferait deux
vérités.

**Une balise sans renommage est NON-CONFIGURÉE** (ADR-047). Elle n'est pas perdue : elle
entre sous sa clé chemin-complet, comme une balise absente de la table. Mais, comme elle,
elle est SIGNALÉE (``routing.tags``) et sa clé est la poignée du curseur
``skip_unconfigured`` (``routing.keys``). Seul le renommage (``meta_renames``) fait d'une
balise une métadonnée configurée.

**Le rôle décide, pas l'emplacement.** ``<META>`` n'est pas un territoire : un ``<LIEN>``
niché dedans reste un lien, et l'aspirer en métadonnée en ferait une seconde vérité.
Seules les balises de rôle ``META`` (et ``VERSION``, qui *est* une métadonnée, sur l'axe
temporel) entrent ici.

**Sauf l'identifiant et la nature.** Ils ont leur champ dédié
(``ParsedDocument.identifier``, ``ParsedDocument.nature``) : les recopier ici en ferait,
là encore, une seconde vérité.

**La clé par défaut est le CHEMIN COMPLET** (ADR-022 §3) : injective par construction,
deux balises homonymes à deux endroits de l'arbre ne s'écrasent plus. Le renommage garde
un nom court : c'est une décision de la table, premier-arrivé-gagne assumé (l'ordre de
préférence des facettes).
"""

from __future__ import annotations

from collections.abc import Iterator

from .role_table import RoleTable
from .roles import Role
from .tree import Node, find_all_with_path, path_key, walk_with_path
from .unconfigured import SourcedFacet, UnconfiguredRouting

__all__ = ["collect_metadata"]

_COLLECTABLE_ROLES = frozenset({Role.META, Role.VERSION})
"""Les rôles qui entrent en métadonnées : ``META``, et ``VERSION``, qui *est* une
métadonnée, sur l'axe temporel."""


def collect_metadata(
    facets: list[SourcedFacet], table: RoleTable, routing: UnconfiguredRouting
) -> None:
    """Range les feuilles collectables dans ``routing.metadata``, et signale celles que
    la table ne renomme pas."""
    for facet, source_file in facets:
        for node, path in _meta_leaves(facet, table):
            rename = table.meta_renames.get(node["tag"])
            key = rename if rename is not None else path_key(path)
            if key in routing.metadata:
                continue
            routing.metadata[key] = node["text"].strip()
            if rename is None:
                routing.tags.setdefault(node["tag"], source_file)
                routing.keys.append(key)


def _meta_leaves(
    facet: Node, table: RoleTable
) -> Iterator[tuple[Node, tuple[str, ...]]]:
    """Les feuilles collectables des conteneurs ``<META>``, avec leur chemin."""
    for container in table.meta_containers:
        for meta, meta_path in find_all_with_path(facet, container):
            yield from (
                (node, path)
                for node, path in walk_with_path(meta, meta_path[:-1])
                if _is_collectable(node, table)
            )


def _is_collectable(node: Node, table: RoleTable) -> bool:
    """Une feuille non vide, de rôle collectable, qui n'a pas son champ dédié
    (l'identifiant, la nature)."""
    return (
        not node["children"]
        and bool(node["text"].strip())
        and node["tag"] not in (table.identifier_tag, table.nature_tag)
        and table.role_of(node["tag"]) in _COLLECTABLE_ROLES
    )
