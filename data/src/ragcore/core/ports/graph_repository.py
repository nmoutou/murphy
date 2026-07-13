from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.enums import SourceName
from ..models.identifiers import OwnerId, SourceIdentifier
from ..models.relation import Relation


@dataclass(frozen=True)
class RelationWriteResult:
    """Ce que l'écriture des arêtes a vraiment fait.

    Le ``None`` que retournait ``upsert_relations`` était le mensonge de comptage
    (§12) : ``RELATION_UPSERTED`` émettait ``count=len(relations)`` — le nombre de
    relations *tentées*. Une arête dont le ``MATCH (b)`` ne trouve rien n'est pas
    écrite, ne lève rien, et n'émettait rien : elle disparaissait en silence.

    Invariant : ``len(written) + len(pending) == len(relations en entrée)``.
    Aucune relation ne se perd entre l'entrée et la sortie — c'est *cela* qui rend
    §12 (comptage exact) et §13 (cache des pendantes) vérifiables.
    """

    written: list[Relation] = field(default_factory=list)
    pending: list[Relation] = field(default_factory=list)


@runtime_checkable
class GraphRepository(Protocol):
    """Stockage du graphe (Neo4j) — merge intelligent (pas de delete-node)."""

    async def initialize(self) -> None:
        """Crée les index Neo4j pour chaque source configurée."""
        ...

    async def merge_document_node(self, document: ParsedDocument) -> None: ...

    async def upsert_relations(self, relations: list[Relation]) -> RelationWriteResult:
        """Écrit les arêtes et RAPPORTE celles dont la cible n'existait pas.

        Une arête dont le ``MATCH (b)`` échoue n'est ni écrite, ni jetée : elle
        remonte dans ``.pending``. C'est l'appelant (ResolveRelationsService) qui
        décide de son sort — le repository, lui, ne connaît pas le cache §13.
        """
        ...

    async def existing_node_ids(
        self, identifiers: list[SourceIdentifier], owner_id: OwnerId
    ) -> set[str]:
        """Sous-ensemble (sérialisé) des identifiants qui existent comme nœuds.

        Retourne des chaînes sérialisées : la comparaison avec les clés du cache
        (§13) se fait ainsi dans le même vocabulaire.
        """
        ...

    async def delete_relations_from(
        self, identifier: SourceIdentifier, owner_id: OwnerId, source: SourceName
    ) -> None:
        """Supprime uniquement les relations sortantes (préserve les entrantes)."""
        ...
