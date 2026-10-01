"""Dépôts en mémoire — la sémantique des vraies bases, sans les bases."""

from collections.abc import Sequence
from dataclasses import dataclass

from ragcore.core.models.chunk import EmbeddedChunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.pending import PendingKey, PendingRelation
from ragcore.core.models.relation import Relation
from ragcore.core.models.unformatted_relation import UnformattedRelation
from ragcore.core.ports.graph_repository import RelationWriteResult


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[str, ParsedDocument] = {}
        self.deleted: list[str] = []

    async def upsert(self, document: ParsedDocument) -> None:
        self.documents[document.identifier.serialize()] = document

    async def delete(self, identifier: Identifier) -> None:
        key = identifier.serialize()
        self.deleted.append(key)
        self.documents.pop(key, None)


class InMemoryVectorRepository:
    def __init__(self) -> None:
        self.chunks: list[EmbeddedChunk] = []
        self.deleted: list[str] = []

    async def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        self.chunks.extend(embedded_chunks)

    async def delete_by_document(self, identifier: Identifier) -> None:
        key = identifier.serialize()
        self.deleted.append(key)
        self.chunks = [
            c for c in self.chunks if c.chunk.parent_identifier.serialize() != key
        ]


class InMemoryGraphRepository:
    """Rejoue le ``MATCH (b)`` de Neo4j : une arête vers une cible inconnue n'est pas
    écrite, et ressort dans ``pending``."""

    def __init__(self) -> None:
        # `edges` porte (arête, run_id) pour la compensation par run
        self.nodes: set[str] = set()
        self.edges: list[tuple[Relation, RunId]] = []

    async def merge_document_node(self, document: ParsedDocument) -> None:
        self.nodes.add(document.identifier.serialize())

    async def upsert_relations(
        self, relations: list[Relation], run_id: RunId
    ) -> RelationWriteResult:
        written: list[Relation] = []
        pending: list[Relation] = []
        for relation in relations:
            source_present = relation.source_identifier.serialize() in self.nodes
            target_present = relation.target_identifier.serialize() in self.nodes
            if source_present and target_present:
                self.edges.append((relation, run_id))
                written.append(relation)
            else:
                pending.append(relation)
        return RelationWriteResult(written=written, pending=pending)

    async def existing_node_ids(self, identifiers: list[Identifier]) -> set[str]:
        return {i.serialize() for i in identifiers} & self.nodes

    async def delete_relations_from(
        self, identifier: Identifier, source: object
    ) -> None:
        del source
        key = identifier.serialize()
        self.edges = [
            (e, rid) for e, rid in self.edges if e.source_identifier.serialize() != key
        ]

    async def delete_relations_by_run(self, run_id: RunId) -> None:
        """Ne défait que les arêtes taguées de ce run."""
        self.edges = [(e, rid) for e, rid in self.edges if rid != run_id]


class InMemoryPendingRepository:
    """Union idempotente sur la clé à trois champs."""

    def __init__(self) -> None:
        self.pendings: dict[PendingKey, PendingRelation] = {}
        self.promotable_calls: list[frozenset[str]] = []

    async def upsert_many(self, pendings: list[PendingRelation]) -> None:
        for pending in pendings:
            existing = self.pendings.get(pending.key)
            if existing is None:
                self.pendings[pending.key] = pending
            else:
                # first_seen_run ne bouge jamais
                self.pendings[pending.key] = existing.model_copy(
                    update={"last_seen_run": pending.last_seen_run}
                )

    async def promotable_for(self, written_node_ids: set[str]) -> list[PendingRelation]:
        self.promotable_calls.append(frozenset(written_node_ids))
        return [p for p in self.pendings.values() if p.target_id in written_node_ids]

    async def delete_many(self, keys: list[PendingKey]) -> None:
        for key in keys:
            self.pendings.pop(key, None)

    async def count(self) -> int:
        return len(self.pendings)


@dataclass(frozen=True)
class StoredUnformatted:
    """La relation et ses deux estampilles de run."""

    relation: UnformattedRelation
    first_seen_run: RunId
    last_seen_run: RunId


UnformattedKey = tuple[str, str, str, str]


class InMemoryUnformattedRepository:
    """Union idempotente sur la clé à quatre champs."""

    def __init__(self) -> None:
        self.rows: dict[UnformattedKey, StoredUnformatted] = {}

    async def upsert_many(
        self, relations: Sequence[UnformattedRelation], run_id: RunId
    ) -> None:
        for relation in relations:
            key = (
                relation.source_identifier.serialize(),
                relation.target_text,
                relation.relation_type,
                relation.sens,
            )
            existing = self.rows.get(key)
            # first_seen_run ne bouge jamais : seul last_seen_run avance
            first_seen_run = existing.first_seen_run if existing else run_id
            self.rows[key] = StoredUnformatted(relation, first_seen_run, run_id)

    async def delete_first_seen(
        self, source_identifier: Identifier, run_id: RunId
    ) -> None:
        source_id = source_identifier.serialize()
        self.rows = {
            key: row
            for key, row in self.rows.items()
            if not (key[0] == source_id and row.first_seen_run == run_id)
        }

    async def count(self) -> int:
        return len(self.rows)
