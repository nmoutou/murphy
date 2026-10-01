"""La transcription XML → arbre, sans perte et sans interprétation, partagée par les
connecteurs de toutes les sources.
"""

from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

__all__ = ["locate_id", "read_root", "to_tree"]


def read_root(path: Path) -> ET.Element | None:
    """``None`` si le fichier est illisible : l'appelant doit le compter
    (``skipped[REASON_UNREADABLE]``)."""
    try:
        return ET.parse(path).getroot()  # noqa: S314 — corpus local, pas une entrée réseau
    except ET.ParseError:
        return None


def to_tree(element: ET.Element) -> dict[str, Any]:
    """Les enfants sont une liste : un dict écraserait les frères homonymes (les
    ``<LIEN>`` d'un article)."""
    return {
        "tag": element.tag,
        "attrib": dict(element.attrib),
        "text": element.text or "",
        "tail": element.tail or "",
        "children": [to_tree(child) for child in element],
    }


def locate_id(element: ET.Element) -> str | None:
    """Le premier ``<ID>`` de l'arbre, sans validation : une clé pour nommer ou grouper.

    La racine peut être l'``<ID>`` elle-même : certains résidus d'export LEGI se
    réduisent à ``<ID>…</ID>``, et le connecteur doit pouvoir les écarter.
    """
    if element.tag == "ID":
        return (element.text or "").strip() or None
    found = element.find(".//ID")
    if found is None:
        return None
    return (found.text or "").strip() or None
