"""Les métadonnées des conteneurs ``<META>``, canonicalisées par la table.

- Le rôle décide, pas l'emplacement : un ``<LIEN>`` dans ``<META>`` reste un lien. Seuls
  les rôles ``META`` et ``VERSION`` entrent ici.
- L'identifiant et la nature ont leur champ dédié. Le titre aussi, par son rôle
  ``TITLE`` (ADR-026) : ``NUM``, titre d'un article mais numéro d'un texte, garde
  ``META``.
- La clé est le chemin complet (ADR-011), ou le nom court du renommage. Une balise sans
  renommage est non configurée (ADR-023) : elle entre quand même, mais signalée.
- Aucune clé n'est injective : chaque valeur s'ajoute à sa clé, et
  ``occurrences.resolve`` tranche (ADR-025).
"""

from __future__ import annotations

from collections.abc import Iterator

from .occurrences import Occurrence
from .role_table import RoleTable
from .roles import Role
from .tree import Node, find_all_with_path, path_key, walk_with_path
from .unconfigured import SourcedFacet, UnconfiguredRouting

__all__ = ["collect_metadata"]

_COLLECTABLE_ROLES = frozenset({Role.META, Role.VERSION})
"""``VERSION`` est une métadonnée, sur l'axe temporel."""


def collect_metadata(
    facets: list[SourcedFacet], table: RoleTable, routing: UnconfiguredRouting
) -> None:
    """Ajoute les feuilles à ``routing.occurrences`` et signale celles que la table ne
    renomme pas."""
    for facet, source_file in facets:
        for node, path in _meta_leaves(facet, table):
            rename = table.meta_renames.get(node["tag"])
            key = rename if rename is not None else path_key(path)
            routing.occurrences[key].append(
                Occurrence(node["text"].strip(), source_file)
            )
            if rename is None:
                routing.tags.setdefault(key, source_file)


def _meta_leaves(
    facet: Node, table: RoleTable
) -> Iterator[tuple[Node, tuple[str, ...]]]:
    for container in table.meta_containers:
        for meta, meta_path in find_all_with_path(facet, container):
            yield from (
                (node, path)
                for node, path in walk_with_path(meta, meta_path[:-1])
                if _is_collectable(node, table)
            )


def _is_collectable(node: Node, table: RoleTable) -> bool:
    return (
        not node["children"]
        and bool(node["text"].strip())
        and node["tag"] not in (table.identifier_tag, table.nature_tag)
        and table.role_of(node["tag"]) in _COLLECTABLE_ROLES
    )
