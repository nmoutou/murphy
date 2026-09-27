"""La relecture de l'arbre transcrit : le connecteur transcrit (``xml_tree``), ces
fonctions relisent.

Un nœud est un dict ``{"tag", "attrib", "text", "tail", "children"}``, tel que
``xml_tree.to_tree`` le produit. Rien ici ne connaît une source : la table de rôles dit
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
    """Comme ``walk``, mais chaque nœud arrive avec son CHEMIN depuis la racine.

    C'est la pièce qui rend l'aplatissement par chemin complet possible (ADR-022 §3) :
    ``walk`` yield des nœuds nus, et une clé construite sur le seul tag produit la
    collision « premier arrivé gagne » — deux ``<NUM>`` à deux endroits de l'arbre
    s'écrasent. Le chemin rend la clé injective par construction.
    """
    path = (*prefix, tree["tag"])
    yield tree, path
    for child in tree["children"]:
        yield from walk_with_path(child, path)


def path_key(path: tuple[str, ...]) -> str:
    """Un chemin de balises → la clé plate canonique (snake_case, jointure ``_``).

    ``("ARTICLE", "META", …, "NUM")`` → ``article_meta_…_num``. La MÊME convention que
    ``title_mapping.sources`` dans ``parameters.yml`` — elle préexistait dans la conf,
    le parser la rejoint.
    """
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
    """Les balises ``tags`` cherchées UNIQUEMENT sous leurs ``containers`` déclarés.

    Rend ``(tag, nœud)`` : la balise trouvée, et le nœud qui la porte.
    """
    for container in containers:
        for parent in find_all(tree, container):
            for tag in tags:
                yield from ((tag, node) for node in find_all(parent, tag))


def first_attr(node: Node, names: Sequence[str]) -> str:
    """Le premier attribut présent, dans l'ordre de préférence donné."""
    for name in names:
        value = node["attrib"].get(name)
        if value:
            return str(value)
    return ""


def holders(block: Node, table: RoleTable) -> list[Node]:
    """Les porteurs de texte d'un bloc — ou le bloc lui-même s'il n'en a pas.

    ``<BLOC_TEXTUEL>`` enveloppe son texte dans ``<CONTENU>`` ; ``<VISAS>`` le porte
    directement. On descend s'il y a un porteur, sinon on lit le bloc.
    """
    for holder_tag in table.text_holders:
        found = find_all(block, holder_tag)
        if found:
            return found
    return [block]


def text_of(node: Node, table: RoleTable) -> str:
    """Le texte d'un nœud, en traversant les balises de mise en forme.

    On ne descend **PAS** dans les balises non transparentes : leur texte est un autre
    champ, pas une continuation de celui-ci. Descendre partout ferait entrer les titres
    et les libellés de liens dans le corps du document.
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
