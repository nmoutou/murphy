"""Le tampon des arêtes de la phase 2 (ADR-034 §5) : écrites dans Neo4j par lots, les
pendantes enregistrées, puis les lignes de transit qui les portaient supprimées.

Un lot peut mêler plusieurs composantes : la réduction est déjà faite.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from ragcore.core.models import PendingRelation, Relation
from ragcore.core.models.audit import build_event
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.pending_repository import PendingRelationRepository
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import RELATION_PENDING, RELATION_UPSERTED

from .run_context import PipelineContext

__all__ = ["RelationWriter", "WriterStores"]

_BUFFER_SIZE = 5_000

Release = Callable[[], Awaitable[None]]
"""Supprime du transit les lignes déjà traitées."""


@dataclass(frozen=True)
class WriterStores:
    graph: GraphRepository
    pending: PendingRelationRepository


class RelationWriter:
    def __init__(
        self,
        stores: WriterStores,
        telemetry: TelemetryPort,
        context: PipelineContext,
    ) -> None:
        self._stores = stores
        self._telemetry = telemetry
        self._context = context
        self._buffer: list[Relation] = []
        self._releases: list[Release] = []
        self.written_count = 0
        self.pending_count = 0

    async def add(self, relations: Sequence[Relation], release: Release) -> None:
        """``release`` ne s'exécute qu'une fois ``relations`` écrites ou en attente :
        une ligne de transit n'est supprimée qu'avec tout ce qu'elle porte."""
        self._buffer.extend(relations)
        self._releases.append(release)
        if len(self._buffer) >= _BUFFER_SIZE:
            await self.flush()

    async def flush(self) -> None:
        buffer, releases = self._buffer, self._releases
        self._buffer, self._releases = [], []
        if buffer:
            await self._write(buffer)
        for release in releases:
            await release()

    async def _write(self, relations: list[Relation]) -> None:
        result = await self._stores.graph.upsert_relations(
            relations, self._context.run_id
        )
        await self._record_pending(result.pending)
        if result.written:
            self._emit(RELATION_UPSERTED, payload={"count": len(result.written)})
        self.written_count += len(result.written)
        self.pending_count += len(result.pending)

    async def _record_pending(self, pending: list[Relation]) -> None:
        if not pending:
            return
        await self._stores.pending.upsert_many(
            [
                PendingRelation.from_relation(relation, self._context.run_id)
                for relation in pending
            ]
        )
        for relation in pending:
            self._emit(
                RELATION_PENDING,
                payload={
                    "target_id": relation.target_identifier.serialize(),
                    "relation_type": relation.relation_type,
                },
                relation=relation,
            )

    def _emit(
        self,
        event_type: str,
        payload: dict[str, object],
        relation: Relation | None = None,
    ) -> None:
        """``relation`` absente : un événement de lot, de la source du run."""
        self._telemetry.emit(
            build_event(
                event_type=event_type,
                run_id=self._context.run_id,
                source=relation.source if relation else self._context.source,
                document_id=(
                    relation.source_identifier.serialize() if relation else None
                ),
                payload=payload,
            )
        )
