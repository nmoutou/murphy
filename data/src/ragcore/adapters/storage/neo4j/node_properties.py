"""Ce que porte un nœud document dans Neo4j : son label et ses propriétés."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType

__all__ = [
    "DOCUMENT_LABEL",
    "TYPE_LABELS",
    "NodeHydration",
    "node_props",
]

DOCUMENT_LABEL = "Document"
"""Le label de tout nœud document, auquel se rattache la contrainte d'unicité
(``schema.py``)."""

TYPE_LABELS: Mapping[DocumentType, str] = {
    DocumentType.ARTICLE: "Article",
    DocumentType.SECTION: "Section",
    DocumentType.TEXTE: "Texte",
    DocumentType.DECISION: "Decision",
}
"""Le second label d'un nœud : son ``document_type``."""


@dataclass(frozen=True)
class NodeHydration:
    """Ce qu'un nœud porte au-delà de ``title`` et ``source`` (ADR-011). Le défaut est
    le nœud maigre de prod ; c'est le plan du run qui l'enrichit en dev.

    - ``metadata`` : les métadonnées en props, clés chemin-complet ;
    - ``include_path`` : les chemins des fichiers source ;
    - ``include_content`` : le texte, sous ``_text_content``.
    """

    metadata: bool = False
    include_path: bool = False
    include_content: bool = False


def node_props(document: ParsedDocument, hydration: NodeHydration) -> dict[str, Any]:
    """Les clés chemin-complet joignent au moins deux segments par `_` : elles ne
    peuvent pas percuter les props de base. `SET d += $props` n'efface pas les props
    d'un run précédent : en dev, c'est `nuke_all` qui repart de zéro.
    """
    props: dict[str, Any] = {
        "title": document.title,
        "source": document.source.value,
    }
    if hydration.metadata:
        props.update(document.metadata)
    if hydration.include_content and document.content:
        props["_text_content"] = document.content
    if hydration.include_path and document.source_files:
        props["source_files"] = list(document.source_files)
    return props
