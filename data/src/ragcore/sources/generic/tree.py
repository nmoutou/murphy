"""La relecture de l'arbre produit par ``xml_tree.to_tree`` : la table de rôles dit
quoi chercher, ces fonctions savent seulement où.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from .role_table import RoleTable

__all__ = [
    "Node",
    "find_all",
    "find_all_with_path",
    "first",
    "first_attr",
    "holders",
    "nested",
    "path_key",
    "text_of",
    "walk",
    "walk_with_path",
]

Node = dict[str, Any]


def walk(tree: Node) -> Iterator[Node]:
    yield tree
    for child in tree["children"]:
        yield from walk(child)


def walk_with_path(
    tree: Node, prefix: tuple[str, ...] = ()
) -> Iterator[tuple[Node, tuple[str, ...]]]:
    """Comme ``walk``, avec le chemin depuis la racine : de quoi construire des clés par
    chemin complet (ADR-011)."""
    path = (*prefix, tree["tag"])
    yield tree, path
    for child in tree["children"]:
        yield from walk_with_path(child, path)


def path_key(path: tuple[str, ...]) -> str:
    """``("ARTICLE", "META", …, "NUM")`` → ``article_meta_…_num``."""
    return "_".join(tag.lower() for tag in path)


def find_all_with_path(tree: Node, tag: str) -> list[tuple[Node, tuple[str, ...]]]:
    return [(node, path) for node, path in walk_with_path(tree) if node["tag"] == tag]


def find_all(tree: Node, tag: str) -> list[Node]:
    return [node for node in walk(tree) if node["tag"] == tag]


def first(tree: Node, tag: str) -> Node | None:
    return next((node for node in walk(tree) if node["tag"] == tag), None)


def nested(
    tree: Node, containers: Sequence[str], tags: Sequence[str]
) -> Iterator[tuple[str, Node]]:
    """Les ``tags`` cherchées seulement sous leurs ``containers``, en ``(tag, nœud)``."""
    for container in containers:
        for parent in find_all(tree, container):
            for tag in tags:
                yield from ((tag, node) for node in find_all(parent, tag))


def first_attr(node: Node, names: Sequence[str]) -> str:
    for name in names:
        value = node["attrib"].get(name)
        if value:
            return str(value)
    return ""


def holders(block: Node, table: RoleTable) -> list[Node]:
    """``<BLOC_TEXTUEL>`` enveloppe son texte dans ``<CONTENU>`` ; ``<VISAS>`` le porte
    directement : sans porteur, on lit le bloc lui-même.
    """
    for holder_tag in table.text_holders:
        found = find_all(block, holder_tag)
        if found:
            return found
    return [block]


def text_of(node: Node, table: RoleTable) -> str:
    """Ne traverse que les balises transparentes : descendre partout ferait entrer
    titres et libellés de liens dans le corps.
    """
    parts: list[str] = []

    def visit(current: Node) -> None:
        if current["text"].strip():
            parts.append(current["text"].strip())
        for child in current["children"]:
            separator = table.transparent.get(child["tag"])
            if separator is not None:
                visit(child)
                parts.append(separator)
            if child["tail"].strip():
                parts.append(child["tail"].strip())

    visit(node)
    return " ".join(parts)
