"""Dépôts en mémoire — la sémantique des vraies bases, sans les bases."""

from ragcore.core.models.chunk import EmbeddedChunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import OwnerId, RunId, SourceIdentifier
from ragcore.core.models.manifest import ManifestEntry
from ragcore.core.models.pending import PendingKey, PendingRelation
from ragcore.core.models.relation import Relation
from ragcore.core.ports.graph_repository import RelationWriteResult


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], ParsedDocument] = {}
        self.deleted: list[tuple[str, str]] = []

    async def upsert(self, document: ParsedDocument) -> None:
        self.documents[(document.identifier.serialize(), document.owner_id)] = document

    async def delete(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None:
        key = (identifier.serialize(), owner_id)
        self.deleted.append(key)
        self.documents.pop(key, None)

    async def get(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> ParsedDocument | None:
        return self.documents.get((identifier.serialize(), owner_id))

    async def exists(self, identifier: SourceIdentifier, owner_id: OwnerId) -> bool:
        return (identifier.serialize(), owner_id) in self.documents


class InMemoryVectorRepository:
    def __init__(self) -> None:
        self.chunks: list[EmbeddedChunk] = []
        self.deleted: list[tuple[str, str]] = []

    async def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        self.chunks.extend(embedded_chunks)

    async def delete_by_document(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> None:
        key = identifier.serialize()
        self.deleted.append((key, owner_id))
        self.chunks = [
            c
            for c in self.chunks
            if not (
                c.chunk.parent_identifier.serialize() == key
                and c.chunk.owner_id == owner_id
            )
        ]


class InMemoryManifestRepository:
    def __init__(self) -> None:
        self.entries: list[ManifestEntry] = []

    async def append(self, entry: ManifestEntry) -> None:
        self.entries.append(entry)

    async def last_for_identifier(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> ManifestEntry | None:
        matches = [
            e
            for e in self.entries
            if e.identifier is not None
            and e.identifier.serialize() == identifier.serialize()
            and e.owner_id == owner_id
        ]
        return matches[-1] if matches else None

    async def last_for_source_path(
        self, source_path: str, owner_id: OwnerId
    ) -> ManifestEntry | None:
        matches = [
            e
            for e in self.entries
            if e.source_path == source_path and e.owner_id == owner_id
        ]
        return matches[-1] if matches else None

    async def delete(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None:
        key = identifier.serialize()
        self.entries = [
            e
            for e in self.entries
            if not (
                e.identifier is not None
                and e.identifier.serialize() == key
                and e.owner_id == owner_id
            )
        ]


class InMemoryGraphRepository:
    """Le fake central du lot 2 : il rejoue le ``MATCH (b)`` de Neo4j.

    Une arête dont la cible n'est pas un nœud connu n'est pas écrite — exactement
    comme en Cypher, où le ``MATCH`` ne matche pas, la requête réussit, et rien
    n'est créé. La différence, ici comme dans le nouveau contrat, c'est qu'on le
    DIT : la relation ressort dans ``pending`` au lieu de disparaître.
    """

    def __init__(self) -> None:
        # Une cible DÉCRITE (`:Unknown`) est un nœud comme un autre côté fake : c'est
        # l'ensemble `nodes` qui rejoue le `MATCH`. `edges` porte (arête, run_id) pour
        # que la compensation par run (§8) ait de quoi filtrer.
        self.nodes: set[str] = set()
        self.edges: list[tuple[Relation, RunId]] = []

    async def initialize(self) -> None:
        return

    async def merge_document_node(self, document: ParsedDocument) -> None:
        self.nodes.add(document.identifier.serialize())

    async def upsert_relations(
        self, relations: list[Relation], run_id: RunId
    ) -> RelationWriteResult:
        written: list[Relation] = []
        pending: list[Relation] = []
        for relation in relations:
            source_present = relation.source_identifier.serialize() in self.nodes
            target = relation.target_identifier
            # La cible DÉCRITE (`unknown:`) est CRÉÉE, jamais différée — comme le vrai
            # repo : elle n'arrivera jamais par un run futur (cf. graph_repository).
            is_described = target.kind == "unknown"
            target_present = target.serialize() in self.nodes or is_described
            if source_present and target_present:
                if is_described:
                    self.nodes.add(target.serialize())
                self.edges.append((relation, run_id))
                written.append(relation)
            else:
                pending.append(relation)
        return RelationWriteResult(written=written, pending=pending)

    async def existing_node_ids(
        self, identifiers: list[SourceIdentifier], owner_id: OwnerId
    ) -> set[str]:
        del owner_id
        return {i.serialize() for i in identifiers} & self.nodes

    async def delete_relations_from(
        self, identifier: SourceIdentifier, owner_id: OwnerId, source: object
    ) -> None:
        del source
        key = identifier.serialize()
        self.edges = [
            (e, rid)
            for e, rid in self.edges
            if not (e.source_identifier.serialize() == key and e.owner_id == owner_id)
        ]

    async def delete_relations_by_run(self, run_id: RunId, owner_id: OwnerId) -> None:
        """§8 : ne défait QUE les arêtes taguées de ce run — pas toutes les sortantes."""
        self.edges = [
            (e, rid)
            for e, rid in self.edges
            if not (rid == run_id and e.owner_id == owner_id)
        ]

    async def compensate_document_node(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> None:
        """§8 : orphelin → supprimé ; cité → dé-hydraté (reste une cible `:Unknown`).

        Le fake modélise la dé-hydratation par « le nœud reste dans `nodes` » : il
        demeure une cible matchable, ce qui est tout ce dont les appelants ont besoin.
        """
        del owner_id
        key = identifier.serialize()
        has_incoming = any(
            e.target_identifier.serialize() == key for e, _ in self.edges
        )
        if not has_incoming:
            self.nodes.discard(key)


class InMemoryPendingRepository:
    """Cache des pendantes — union idempotente sur la clé à quatre champs (§13)."""

    def __init__(self) -> None:
        self.pendings: dict[PendingKey, PendingRelation] = {}
        self.promotable_calls: list[tuple[frozenset[str], str]] = []

    async def upsert_many(self, pendings: list[PendingRelation]) -> None:
        for pending in pendings:
            existing = self.pendings.get(pending.key)
            if existing is None:
                self.pendings[pending.key] = pending
            else:
                # first_seen_run ne bouge jamais : c'est la date de naissance du trou.
                self.pendings[pending.key] = existing.model_copy(
                    update={"last_seen_run": pending.last_seen_run}
                )

    async def promotable_for(
        self, written_node_ids: set[str], owner_id: OwnerId
    ) -> list[PendingRelation]:
        self.promotable_calls.append((frozenset(written_node_ids), owner_id))
        return [
            p
            for p in self.pendings.values()
            if p.owner_id == owner_id and p.target_id in written_node_ids
        ]

    async def delete_many(self, keys: list[PendingKey]) -> None:
        for key in keys:
            self.pendings.pop(key, None)

    async def count_for_owner(self, owner_id: OwnerId) -> int:
        return sum(1 for p in self.pendings.values() if p.owner_id == owner_id)
