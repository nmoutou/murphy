"""La structure déclarée d'un document : ses liens bruts et ses ancêtres.

Le vocabulaire de la source reste tel quel : seul ``core/links`` le traduit, pour que
la table de traduction ne vive qu'à un endroit.
"""

from __future__ import annotations

from typing import Any

from ragcore.core.links import VERSION_KIND

from .normalize import normalize_text
from .role_table import RoleTable
from .tree import Node, find_all, first_attr, nested, text_of

__all__ = ["read_context", "read_references"]


def read_references(facets: list[Node], table: RoleTable) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for facet in facets:
        references.extend(_declared_links(facet, table))
        references.extend(_structural_links(facet, table))
        references.extend(_version_links(facet, table))
    return references


def _declared_links(facet: Node, table: RoleTable) -> list[dict[str, Any]]:
    return [
        {
            "kind": tag,
            "id": lien["attrib"].get("id", ""),
            "typelien": lien["attrib"].get("typelien", ""),
            "sens": lien["attrib"].get("sens", ""),
            "label": normalize_text(text_of(lien, table)),
        }
        for tag in table.link_tags
        for lien in find_all(facet, tag)
    ]


def _structural_links(facet: Node, table: RoleTable) -> list[dict[str, Any]]:
    """Cherchés seulement dans leurs conteneurs déclarés : sous ``<VERSIONS>``, un
    ``LIEN_ART`` désigne une autre version du même article, pas une contenance.
    """
    return [
        {
            "kind": tag,
            "id": lien["attrib"].get("id", ""),
            "label": normalize_text(text_of(lien, table)),
        }
        for tag, lien in nested(
            facet, table.link_containers, table.structural_link_tags
        )
    ]


def _version_links(facet: Node, table: RoleTable) -> list[dict[str, Any]]:
    """La datation voyage avec la référence, jusqu'à l'arête."""
    return [
        {
            "kind": VERSION_KIND,
            "id": lien["attrib"].get("id", ""),
            **{
                name: str(value)
                for name, value in lien["attrib"].items()
                if name != "id" and str(value).strip()
            },
        }
        for _, lien in nested(
            facet, table.version_link_containers, table.version_link_tags
        )
    ]


def read_context(facets: list[Node], table: RoleTable) -> list[dict[str, Any]]:
    """Tous les ancêtres, pas seulement le parent : ``<CONTEXTE>`` déclare la fermeture
    transitive, que ``relation_reduction`` réduit en phase 2.
    """
    context: list[dict[str, Any]] = []
    for facet in facets:
        for tag, node in nested(facet, table.ancestor_containers, table.ancestor_tags):
            ancestor = first_attr(node, table.ancestor_id_attrs)
            if ancestor:
                context.append(
                    {"kind": tag, "id": ancestor, "label": normalize_text(node["text"])}
                )
    return context
