"""La phase 2 : les arêtes, lues dans ``transit_relations`` (ADR-034 §5).

Suppose que tous les nœuds du run existent : c'est l'arête du DAG entre les phases 1
et 2 qui le garantit. Seul ce service touche au registre des pendantes.

- Les verbes réductibles se réduisent composante connexe par composante connexe : la
  plus grande borne la mémoire. Aucun plafond : couper une composante rendrait la
  réduction approximative.
- Les autres verbes traversent par lots, sans réduction.
- Une ligne de transit n'est supprimée qu'une fois tout ce qu'elle porte écrit, mis en
  attente ou réduit ; la collection doit être vide en fin de phase (§6).
"""

import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import partial

from ragcore.core.exceptions import TransitNotDrainedError
from ragcore.core.models import PendingRelation, Relation
from ragcore.core.models.audit import build_event
from ragcore.core.models.pending import PendingKey
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.pending_repository import PendingRelationRepository
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.ports.transit_repository import TransitRelationRepository
from ragcore.core.services.connected_components import Component, ConnectedComponents
from ragcore.core.services.relation_reduction import (
    REDUCIBLE_TYPES,
    reduce_transitively,
)
from ragcore.core.statistics_measures import COMPONENT_NODES, COMPONENT_RELATIONS
from ragcore.core.telemetry_events import RELATION_PROMOTED

from .relation_writer import RelationWriter, WriterStores
from .run_context import PipelineContext

__all__ = ["ComponentsByVerb", "ResolutionOutcome", "ResolveRelationsService"]

logger = logging.getLogger(__name__)

_COMPONENT_READ_BUDGET = 10_000
"""Les nœuds dont les arêtes sont lues ensemble : les petites composantes partagent un
aller-retour, une grande le prend seule."""

_OTHERS_BATCH_SIZE = 5_000

ComponentsByVerb = Mapping[str, list[Component]]


@dataclass(frozen=True)
class ResolutionOutcome:
    """La sortie du nœud de phase 2. ``extracted == written + pending + reduced``."""

    written_count: int
    """Réellement écrites, pas tentées."""
    pending_count: int
    """Différées : une extrémité n'est pas (encore) dans le corpus."""
    promoted_count: int
    """Pendantes de runs passés, résolues parce que leur extrémité manquante vient
    d'arriver."""
    reduced_count: int
    """Redondantes, éliminées par la réduction transitive : ni écrites ni pendantes."""
    extracted_count: int
    """Lues en transit : une par déclaration, doublons compris."""


@dataclass
class _Run:
    context: PipelineContext
    writer: RelationWriter
    read: int = 0
    reduced: int = 0


class ResolveRelationsService:
    def __init__(
        self,
        graph_repo: GraphRepository,
        pending_repo: PendingRelationRepository,
        transit_repo: TransitRelationRepository,
        telemetry: WorkerTelemetry,
    ) -> None:
        self._graph_repo = graph_repo
        self._pending_repo = pending_repo
        self._transit_repo = transit_repo
        self._telemetry = telemetry

    async def find_components(self, context: PipelineContext) -> ComponentsByVerb:
        """La première passe : les couples de chaque verbe réductible, lus en flux."""
        found: dict[str, list[Component]] = {}
        for verb in sorted(REDUCIBLE_TYPES):
            components = ConnectedComponents()
            async for source, target in self._transit_repo.pairs(context.run_id, verb):
                components.add_edge(source, target)
            found[verb] = components.components()
            logger.info("Phase 2 : %d composantes « %s »", len(found[verb]), verb)
        return found

    async def execute(
        self,
        components: ComponentsByVerb,
        written_node_ids: set[str],
        context: PipelineContext,
    ) -> ResolutionOutcome:
        """Lève ``TransitNotDrainedError`` si une relation reste en transit."""
        # Avant les écritures : les pendantes du run naissent quand tous ses nœuds
        # existent, les rejouer échouerait à coup sûr
        promoted_count = await self._promote(written_node_ids, context)
        stores = WriterStores(self._graph_repo, self._pending_repo)
        run = _Run(context, RelationWriter(stores, self._telemetry, context))
        for verb, found in components.items():
            await self._reduce_verb(verb, found, run)
        await self._write_others(run)
        await run.writer.flush()
        await self._ensure_drained()
        return ResolutionOutcome(
            written_count=run.writer.written_count,
            pending_count=run.writer.pending_count,
            promoted_count=promoted_count,
            reduced_count=run.reduced,
            extracted_count=run.read,
        )

    async def _reduce_verb(
        self, verb: str, components: list[Component], run: _Run
    ) -> None:
        run_id = run.context.run_id
        for group in _read_groups(components):
            sources = [node for component in group for node in component.nodes]
            relations = await self._transit_repo.read_by_sources(run_id, verb, sources)
            kept = self._reduce_group(group, relations)
            run.read += len(relations)
            run.reduced += len(relations) - len(kept)
            release = partial(
                self._transit_repo.delete_by_sources, run_id, verb, sources
            )
            await run.writer.add(kept, release)

    def _reduce_group(
        self, group: list[Component], relations: list[Relation]
    ) -> list[Relation]:
        """Chaque composante seule : ses arêtes partent toutes d'un de ses nœuds."""
        position = {
            node: i for i, component in enumerate(group) for node in component.nodes
        }
        by_component: list[list[Relation]] = [[] for _ in group]
        for relation in relations:
            by_component[position[relation.source_identifier.serialize()]].append(
                relation
            )
        kept: list[Relation] = []
        for component, own in zip(group, by_component, strict=True):
            self._measure(component)
            kept.extend(reduce_transitively(own))
        return kept

    async def _write_others(self, run: _Run) -> None:
        batches = self._transit_repo.batches_excluding(
            run.context.run_id, REDUCIBLE_TYPES, _OTHERS_BATCH_SIZE
        )
        async for batch in batches:
            run.read += len(batch.relations)
            release = partial(self._transit_repo.delete_rows, batch)
            await run.writer.add(batch.relations, release)

    def _measure(self, component: Component) -> None:
        self._telemetry.record_measure(
            COMPONENT_NODES, len(component.nodes), component.name
        )
        self._telemetry.record_measure(
            COMPONENT_RELATIONS, component.relations, component.name
        )

    async def _ensure_drained(self) -> None:
        remaining = await self._transit_repo.count()
        if remaining:
            msg = (
                f"transit_relations garde {remaining} relation(s) en fin de phase 2 : "
                "ni écrites, ni mises en attente, ni réduites. Un bug de la phase 2 "
                "(ADR-034 §6)."
            )
            raise TransitNotDrainedError(msg)

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
            self._telemetry.log(
                "info",
                "relation.promotion.still_pending",
                count=len(result.pending),
            )

        written_keys = {PendingKey.from_relation(r) for r in result.written}
        promoted = [c for c in candidates if c.key in written_keys]

        await self._pending_repo.delete_many([c.key for c in promoted])
        for candidate in promoted:
            self._emit_promoted(candidate, context)
        return len(promoted)

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


def _read_groups(components: list[Component]) -> Iterator[list[Component]]:
    """Des composantes consécutives, jusqu'au budget de nœuds."""
    group: list[Component] = []
    size = 0
    for component in components:
        if group and size + len(component.nodes) > _COMPONENT_READ_BUDGET:
            yield group
            group, size = [], 0
        group.append(component)
        size += len(component.nodes)
    if group:
        yield group
