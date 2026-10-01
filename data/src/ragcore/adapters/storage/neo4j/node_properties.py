"""Ce que porte un nœud document dans Neo4j : son label et ses propriétés."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import IDENTIFIER_PREFIX_LENGTH, Identifier

__all__ = [
    "DEFAULT_LABEL",
    "NodeHydration",
    "NodeLabels",
    "node_props",
]

DEFAULT_LABEL = "Document"
"""Le label d'un document dont aucune source ne déclare le préfixe (les décisions)."""

_LABEL_PATTERN = re.compile(r"[A-Z][A-Za-z0-9]*")
_PREFIX_PATTERN = re.compile(rf"[A-Z]{{{IDENTIFIER_PREFIX_LENGTH}}}")


@dataclass(frozen=True)
class NodeLabels:
    """Le label d'un nœud document, décidé par le préfixe de son identifiant.

    Une DONNÉE, déclarée par chaque source (``sources/registry.py``) : le préfixe
    ``LEGIARTI`` donne ``Article``, et un préfixe que la table ne connaît pas reçoit
    ``DEFAULT_LABEL``.

    Les labels sont validés à la construction : un label mal formé arrête le run ici,
    avec un message, plutôt qu'à la première écriture d'un nœud dans Neo4j.
    """

    by_prefix: Mapping[str, str]

    def __post_init__(self) -> None:
        for prefix in self.by_prefix:
            if not _PREFIX_PATTERN.fullmatch(prefix):
                raise ValueError(
                    f"Préfixe d'identifiant invalide dans les labels Neo4j : {prefix!r} "
                    f"(attendu : {IDENTIFIER_PREFIX_LENGTH} majuscules, p. ex. LEGIARTI)."
                )
        for label in self.by_prefix.values():
            if not _LABEL_PATTERN.fullmatch(label):
                raise ValueError(
                    f"Label Neo4j invalide : {label!r} (attendu : une majuscule puis "
                    "des lettres ou chiffres)."
                )

    def label_for(self, identifier: Identifier) -> str:
        return self.by_prefix.get(identifier.prefix, DEFAULT_LABEL)


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
