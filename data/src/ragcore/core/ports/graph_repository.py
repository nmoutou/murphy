from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.enums import SourceName
from ..models.identifiers import Identifier, RunId
from ..models.relation import Relation


@dataclass(frozen=True)
class RelationWriteResult:
    """Ce que l'écriture des arêtes a vraiment fait : une arête dont le ``MATCH (b)``
    échoue n'est pas écrite et ne lève rien.

    Invariant : ``len(written) + len(pending) == len(relations en entrée)``.
    """

    written: list[Relation] = field(default_factory=list)
    pending: list[Relation] = field(default_factory=list)


@runtime_checkable
class GraphRepository(Protocol):
    """Stockage du graphe (Neo4j) — merge, jamais de suppression de nœud."""

    async def merge_document_node(self, document: ParsedDocument) -> None: ...

    async def upsert_relations(
        self, relations: list[Relation], run_id: RunId
    ) -> RelationWriteResult:
        """Une arête dont la cible n'existe pas remonte dans ``.pending`` ; l'appelant
        décide de son sort.

        ``run_id`` tague chaque arête écrite : c'est ce qui permet de compenser un run
        sans toucher aux arêtes posées par un autre.
        """
        ...

    async def delete_relations_by_run(self, run_id: RunId) -> None:
        """Supprime les arêtes taguées de ce run, et elles seules : un run ne peut
        défaire que son propre ouvrage."""
        ...

    async def existing_node_ids(self, identifiers: list[Identifier]) -> set[str]:
        """Sous-ensemble, sérialisé comme les clés des pendantes, des identifiants qui
        existent comme nœuds.

        Pas encore appelée en production (le rejeu ciblé n'est pas câblé) : elle sert
        aux tests d'intégration.
        """
        ...

    async def delete_relations_from(
        self, identifier: Identifier, source: SourceName
    ) -> None:
        """Les sortantes seulement ; les entrantes sont préservées."""
        ...
