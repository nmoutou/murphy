"""Ce que porte un nœud document dans Neo4j : son label et ses propriétés."""

from dataclasses import dataclass
from typing import Any

from ragcore.core.models.document import ParsedDocument

__all__ = ["CITATIONS_PROP", "NodeHydration", "node_label", "node_props"]

_DEFAULT_LABEL = "Document"
_UNKNOWN_DOCUMENT_TYPE = "inconnu"


@dataclass(frozen=True)
class NodeHydration:
    """Ce qu'un nœud document porte AU-DELÀ de ses trois props de base (ADR-022 §2).

    Le défaut est le régime PROD : nœud maigre (``title``, ``source``,
    ``schema_version``), rien d'autre. C'est le constructeur — le hook — qui ouvre les
    vannes en dev (``resolve_node_hydration``), jamais ce module : le défaut penche
    vers le refus, comme ``nuke_all`` et l'interrupteur d'embedding.

    - ``metadata`` : les métadonnées du document en props (clés chemin-complet,
      valeurs chaînes). Neo4j est l'outil d'inspection privilégié de la v0 — un nœud
      maigre est un obstacle à l'itération sur le modèle de données.
    - ``include_path`` : les chemins des FICHIERS source (``document.source_files``).
      Un chemin absolu du poste d'ingestion n'a de sens qu'en dev.
    - ``include_content`` : le texte du document, sous la prop ``_text_content``
      (convention ``_text_`` du cadrage B-00-d). Les sections n'ont pas de prop à
      elles : chaque section est un morceau LITTÉRAL de ``content`` (invariant du
      parser) — ``_text_content`` les contient toutes.
    """

    metadata: bool = False
    include_path: bool = False
    include_content: bool = False


CITATIONS_PROP = "citations"
"""La prop qui porte les cibles décrites, en **JSON sérialisé**.

Neo4j ne stocke pas d'objet imbriqué : une propriété est un scalaire ou un tableau de
scalaires. Trois listes parallèles (``citation_texts``, ``citation_verbs``,
``citation_sens``) exprimeraient la même chose sans garantir qu'elles restent alignées —
une désynchronisation y serait invisible et silencieuse. Un JSON par citation garde
chaque triplet solidaire.
"""


def _citation_props(document: ParsedDocument) -> dict[str, Any]:
    """Les citations du document, prêtes pour ``SET d += $props``.

    Rend un dict VIDE quand il n'y en a pas, plutôt qu'une liste vide : ``SET d +=``
    écrirait sinon une prop vide sur les ~99 % de documents qui ne citent rien de décrit.
    """
    if not document.citations:
        return {}
    return {
        CITATIONS_PROP: [c.model_dump_json() for c in document.citations],
    }


def node_label(document: ParsedDocument) -> str:
    """Le label du nœud, déduit du ``document_type`` de l'identifiant."""
    doc_type = getattr(document.identifier, "document_type", None)
    if doc_type and doc_type != _UNKNOWN_DOCUMENT_TYPE:
        return str(doc_type).capitalize()
    return _DEFAULT_LABEL


def node_props(document: ParsedDocument, hydration: NodeHydration) -> dict[str, Any]:
    """Les propriétés du nœud : les trois de base, les citations, puis l'hydratation.

    L'hydratation de dev (ADR-022 §2). Les clés chemin-complet des métadonnées ne
    peuvent pas percuter les props de base — elles joignent ≥ 2 segments par `_`.
    `SET d += $props` n'efface pas les props d'un run précédent : en dev, c'est
    `nuke_all` qui repart de zéro (les données sont jetables en v0).
    """
    props: dict[str, Any] = {
        "title": document.title,
        "source": document.source.value,
        "schema_version": document.schema_version,
        **_citation_props(document),
    }
    if hydration.metadata:
        props.update(document.metadata)
    if hydration.include_content and document.content:
        props["_text_content"] = document.content
    if hydration.include_path and document.source_files:
        props["source_files"] = list(document.source_files)
    return props
