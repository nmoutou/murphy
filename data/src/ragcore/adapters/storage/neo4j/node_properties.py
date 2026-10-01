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
"""Le label de TOUT nœud document. Il ne change jamais : la contrainte d'unicité sur
``identifier`` (``schema.py``) s'y rattache, et toute recherche par identifiant passe
par lui."""

TYPE_LABELS: Mapping[DocumentType, str] = {
    DocumentType.ARTICLE: "Article",
    DocumentType.SECTION: "Section",
    DocumentType.TEXTE: "Texte",
    DocumentType.DECISION: "Decision",
}
"""Le second label d'un nœud : son ``document_type``, le même que dans Mongo et Qdrant."""


@dataclass(frozen=True)
class NodeHydration:
    """Ce qu'un nœud document porte AU-DELÀ de ses deux props de base (ADR-022 §2).

    Le défaut est le régime PROD : nœud maigre (``title``, ``source``), rien d'autre.
    C'est le plan du run qui ouvre les vannes en dev (``include_path`` et
    ``include_content_neo4j`` de ``parameters.yml``), jamais ce module : le défaut penche vers le refus, comme
    ``nuke_all`` et l'interrupteur d'embedding.

    - ``metadata`` : les métadonnées du document en props (clés chemin-complet,
      valeurs chaînes). Neo4j est l'outil d'inspection privilégié de la v0 — un nœud
      maigre est un obstacle à l'itération sur le modèle de données.
    - ``include_path`` : les chemins des FICHIERS source (``document.source_files``).
      Un chemin absolu du poste d'ingestion n'a de sens qu'en dev. Le même réglage les
      écrit dans le document Mongo.
    - ``include_content`` : le texte du document, sous la prop ``_text_content``
      (convention ``_text_``). Les sections n'ont pas de prop à
      elles : chaque section est un morceau LITTÉRAL de ``content`` (invariant du
      parser) — ``_text_content`` les contient toutes.
    """

    metadata: bool = False
    include_path: bool = False
    include_content: bool = False


def node_props(document: ParsedDocument, hydration: NodeHydration) -> dict[str, Any]:
    """Les propriétés du nœud : les deux de base, puis l'hydratation.

    L'hydratation de dev (ADR-022 §2). Les clés chemin-complet des métadonnées ne
    peuvent pas percuter les props de base — elles joignent ≥ 2 segments par `_`.
    `SET d += $props` n'efface pas les props d'un run précédent : en dev, c'est
    `nuke_all` qui repart de zéro (les données sont jetables en v0).
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
