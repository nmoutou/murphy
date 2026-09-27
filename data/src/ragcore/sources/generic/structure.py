"""La structure déclarée d'un document : ses liens bruts et ses ancêtres.

Le parser rend le vocabulaire de la source tel quel (``typelien``, ``sens``, ``id``) ;
c'est ``core/links`` qui le traduit, et qui déclare ce qu'il ne sait pas traduire. Typer
ici mettrait la table de traduction dans deux modules à la fois — et c'est exactement
ainsi qu'elles divergent.
"""

from __future__ import annotations

from typing import Any

from ragcore.core.links import VERSION_KIND

from .normalize import normalize_text
from .role_table import RoleTable
from .tree import Node, find_all, first_attr, nested, text_of

__all__ = ["read_context", "read_references"]


def read_references(facets: list[Node], table: RoleTable) -> list[dict[str, Any]]:
    """Les liens déclarés, **BRUTS** — le parser ne les type pas."""
    references: list[dict[str, Any]] = []
    for facet in facets:
        references.extend(_declared_links(facet, table))
        references.extend(_structural_links(facet, table))
        references.extend(_version_links(facet, table))
    return references


def _declared_links(facet: Node, table: RoleTable) -> list[dict[str, Any]]:
    """Les liens typés par la source (``typelien``/``sens``), où qu'ils soient."""
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
    """Les liens STRUCTURELS : cherchés UNIQUEMENT dans leurs conteneurs déclarés.

    Sous ``<VERSIONS>``, un ``LIEN_ART`` désigne les autres versions du MÊME article —
    pas une contenance : il a son propre circuit (``_version_links``).
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
    """Les liens de VERSION : l'axe temporel, sous son kind dédié. La datation
    (debut/fin/etat/num) voyage avec la référence — elle finira sur l'arête."""
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
    """Les ANCÊTRES du document.

    ``<CONTEXTE>`` déclare la *fermeture transitive* de la contenance — jusqu'à neuf
    niveaux d'un coup, pas seulement le parent direct. C'est la raison d'être de
    ``core/services/relation_reduction`` : l'union de cette fermeture et de l'arbre
    déclaré par les sections doit être réduite pour redonner l'arbre.
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
