"""Ce que porte un nœud document dans Neo4j : son label et ses propriétés."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import IDENTIFIER_PREFIX_LENGTH, Identifier

__all__ = [
    "DEFAULT_LABEL",
    "PENDING_LABEL",
    "NodeHydration",
    "NodeLabels",
    "node_props",
]

PENDING_LABEL = "Pending"
"""L'état d'un nœud CITÉ dont le document a été compensé — ou n'est pas encore arrivé.

Ne pas confondre avec l'ancien ``:Unknown``, qui confondait deux choses très
différentes : (a) une cible *décrite en français*, qui n'arrivera jamais et n'est pas un
document — elle est désormais une ``UnformattedRelation``, hors du graphe ; (b) une
cible *identifiée* dont le document manque à l'appel, et qui peut parfaitement arriver
au prochain run. Seul (b) mérite un nœud, et c'est celui-ci.

``merge_document_node`` le ré-hydrate sans rien de spécial : son ``MERGE`` porte sur le
seul ``identifier`` et retombe sur ce nœud quel que soit son label.
"""

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

    Les labels sont validés à la construction, parce qu'ils finissent dans le TEXTE
    d'une requête Cypher (``REMOVE n:Article:Texte…`` à la dé-hydratation) : un label
    mal formé arrête le run ici, avec un message, plutôt que dans Neo4j.
    """

    by_prefix: Mapping[str, str]

    def __post_init__(self) -> None:
        for prefix in self.by_prefix:
            if not _PREFIX_PATTERN.fullmatch(prefix):
                raise ValueError(
                    f"Préfixe d'identifiant invalide dans les labels Neo4j : {prefix!r} "
                    f"(attendu : {IDENTIFIER_PREFIX_LENGTH} majuscules, p. ex. LEGIARTI)."
                )
        for label in self.known:
            if not _LABEL_PATTERN.fullmatch(label) or label == PENDING_LABEL:
                raise ValueError(
                    f"Label Neo4j invalide : {label!r} (attendu : une majuscule puis "
                    f"des lettres ou chiffres ; {PENDING_LABEL!r} est réservé)."
                )

    @property
    def known(self) -> tuple[str, ...]:
        """Tous les labels que cette table peut poser, sans doublon."""
        return tuple(dict.fromkeys((DEFAULT_LABEL, *self.by_prefix.values())))

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
