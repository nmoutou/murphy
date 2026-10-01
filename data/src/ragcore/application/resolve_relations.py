"""La phase 2 : les arêtes, en batch.

Suppose que tous les nœuds du run existent : c'est l'arête du DAG entre les phases 1
et 2 qui le garantit. Seul ce service touche au registre des pendantes.
"""

from dataclasses import dataclass

from ragcore.core.models import PendingRelation, Relation, RunStats
from ragcore.core.models.audit import build_event
from ragcore.core.models.pending import PendingKey
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.pending_repository import PendingRelationRepository
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.services.relation_reduction import reduce_transitively
from ragcore.core.telemetry_events import (
    RELATION_PENDING,
    RELATION_PROMOTED,
    RELATION_UPSERTED,
)

from .run_context import PipelineContext

__all__ = ["ResolutionOutcome", "ResolveRelationsService"]


@dataclass(frozen=True)
class ResolutionOutcome:
    """La sortie du nœud de phase 2."""

    stats: RunStats
    written_count: int
    """Réellement écrites, pas tentées."""
    pending_count: int
    """Différées : leur cible n'est pas (encore) dans le corpus."""
    promoted_count: int
    """Pendantes de runs passés, résolues parce que leur cible vient d'arriver."""

    reduced_count: int = 0
    """Redondantes, éliminées par la réduction transitive : ni écrites ni pendantes."""


class ResolveRelationsService:
    def __init__(
        self,
        graph_repo: GraphRepository,
        pending_repo: PendingRelationRepository,
        telemetry: TelemetryPort,
    ) -> None:
        self._graph_repo = graph_repo
        self._pending_repo = pending_repo
        self._telemetry = telemetry

    async def execute(
        self,
        relations: list[Relation],
        written_node_ids: set[str],
        context: PipelineContext,
    ) -> ResolutionOutcome:
        stats = RunStats.empty()

        # À l'échelle du corpus : la hiérarchie d'un article se déclare aussi dans
        # d'autres fichiers
        submitted = len(relations)
        relations = reduce_transitively(relations)
        reduced_count = submitted - len(relations)

        result = await self._graph_repo.upsert_relations(relations, context.run_id)

        await self._record_pending(result.pending, context)
        if result.pending:
            stats = stats.with_count(RELATION_PENDING, len(result.pending))

        if result.written:
            self._announce_written(result.written, context)
            stats = stats.with_count(RELATION_UPSERTED)

        # Ne retente que les pendantes dont la cible vient d'arriver : le coût suit le
        # delta du run, jamais la taille du backlog
        promoted_count = await self._promote(written_node_ids, context)
        if promoted_count:
            stats = stats.with_count(RELATION_PROMOTED, promoted_count)

        return ResolutionOutcome(
            stats=stats,
            written_count=len(result.written),
            pending_count=len(result.pending),
            promoted_count=promoted_count,
            reduced_count=reduced_count,
        )

    async def _promote(
        self, written_node_ids: set[str], context: PipelineContext
    ) -> int:
        candidates = await self._pending_repo.promotable_for(written_node_ids)
        if not candidates:
            return 0

        result = await self._graph_repo.upsert_relations(
            [candidate.to_relation() for candidate in candidates], context.run_id
        )

        if result.pending:
            # La cible vient d'être écrite : c'est la source qui manque. La pendante
            # reste.
            self._telemetry.log(
                "warning",
                "relation.promotion.incomplete",
                count=len(result.pending),
            )

        written_keys = {PendingKey.from_relation(r) for r in result.written}
        promoted = [c for c in candidates if c.key in written_keys]

        await self._pending_repo.delete_many([c.key for c in promoted])
        for candidate in promoted:
            self._emit_promoted(candidate, context)
        return len(promoted)

    async def _record_pending(
        self, pending: list[Relation], context: PipelineContext
    ) -> None:
        if not pending:
            return
        await self._pending_repo.upsert_many(
            [
                PendingRelation.from_relation(relation, context.run_id)
                for relation in pending
            ]
        )
        for relation in pending:
            self._emit_relation(RELATION_PENDING, relation, context)

    def _announce_written(
        self, written: list[Relation], context: PipelineContext
    ) -> None:
        """`count` porte les arêtes réussies, pas tentées."""
        self._telemetry.emit(
            build_event(
                event_type=RELATION_UPSERTED,
                run_id=context.run_id,
                source=context.source,
                payload={"count": len(written)},
            )
        )

    def _emit_promoted(
        self, candidate: PendingRelation, context: PipelineContext
    ) -> None:
        self._telemetry.emit(
            build_event(
                event_type=RELATION_PROMOTED,
                run_id=context.run_id,
                source=candidate.source,
                document_id=candidate.source_id,
                payload={
                    "target_id": candidate.target_id,
                    "relation_type": candidate.relation_type,
                    "first_seen_run": candidate.first_seen_run,
                },
            )
        )

    def _emit_relation(
        self, event_type: str, relation: Relation, context: PipelineContext
    ) -> None:
        self._telemetry.emit(
            build_event(
                event_type=event_type,
                run_id=context.run_id,
                source=relation.source,
                document_id=relation.source_identifier.serialize(),
                payload={
                    "target_id": relation.target_identifier.serialize(),
                    "relation_type": relation.relation_type,
                },
            )
        )
