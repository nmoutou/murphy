"""Les métadonnées des conteneurs ``<META>``, canonicalisées par la table.

Ni le contenu ni les liens n'y sont : ils ont leur place, et la dupliquer ferait deux
vérités.

**Une balise sans renommage est NON-CONFIGURÉE** (ADR-047). Elle n'est pas perdue : elle
entre sous sa clé chemin-complet, comme une balise absente de la table. Mais, comme elle,
elle est SIGNALÉE sous sa clé (``routing.tags``), qui est aussi la poignée du curseur
``skip_unconfigured``. Seul le renommage (``meta_renames``) fait d'une
balise une métadonnée configurée.

**Le rôle décide, pas l'emplacement.** ``<META>`` n'est pas un territoire : un ``<LIEN>``
niché dedans reste un lien, et l'aspirer en métadonnée en ferait une seconde vérité.
Seules les balises de rôle ``META`` (et ``VERSION``, qui *est* une métadonnée, sur l'axe
temporel) entrent ici.

**Sauf l'identifiant, la nature et le titre.** Ils ont leur champ dédié
(``ParsedDocument.identifier``, ``ParsedDocument.nature``, ``ParsedDocument.title``) :
les recopier ici en ferait, là encore, une seconde vérité (ADR-050). Une balise de titre
que la table renomme reste une métadonnée : ``NUM`` → ``num`` est le titre d'un article,
mais le numéro d'un texte, et le renommage est une promotion explicite.

**La clé par défaut est le CHEMIN COMPLET** (ADR-022 §3), le renommage donne un nom court.
Aucune des deux n'est injective : deux balises sœurs homonymes ont le même chemin, et une
même balise renommée revient dans chaque facette. Rien n'est donc tranché ici : chaque
valeur s'AJOUTE à sa clé, dans l'ordre de lecture, et ``occurrences.resolve`` décide une
fois — dédoublonner, lister, ou refuser le document (ADR-049).
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
"""Les rôles qui entrent en métadonnées : ``META``, et ``VERSION``, qui *est* une
métadonnée, sur l'axe temporel."""


def collect_metadata(
    facets: list[SourcedFacet], table: RoleTable, routing: UnconfiguredRouting
) -> None:
    """Ajoute les feuilles collectables à ``routing.occurrences``, et signale celles que
    la table ne renomme pas."""
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
    """Les feuilles collectables des conteneurs ``<META>``, avec leur chemin."""
    for container in table.meta_containers:
        for meta, meta_path in find_all_with_path(facet, container):
            yield from (
                (node, path)
                for node, path in walk_with_path(meta, meta_path[:-1])
                if _is_collectable(node, table)
            )


def _is_collectable(node: Node, table: RoleTable) -> bool:
    """Une feuille non vide, de rôle collectable, qui n'a pas son champ dédié."""
    return (
        not node["children"]
        and bool(node["text"].strip())
        and not _has_dedicated_field(node["tag"], table)
        and table.role_of(node["tag"]) in _COLLECTABLE_ROLES
    )


def _has_dedicated_field(tag: str, table: RoleTable) -> bool:
    """L'identifiant, la nature, et les balises de titre que la table ne renomme pas."""
    if tag in (table.identifier_tag, table.nature_tag):
        return True
    return tag in table.title_tags and tag not in table.meta_renames
