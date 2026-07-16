"""ResolveRelationsService — la phase 2 : les arêtes, en batch, après la barrière.

La barrière n'est pas dans ce fichier : c'est l'arête du DAG entre le node de
phase 1 et celui de phase 2. Ce service tient pour acquis que tous les nœuds du run
existent déjà — et c'est le pipeline, pas un ``join()`` enfoui, qui le garantit.
L'hypothèse est donc déclarée, jamais implicite.

Ce service possède le registre des pendantes (§13). Personne d'autre n'y touche.
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
    """La sortie du node de phase 2 — de la donnée, comme la phase 1."""

    stats: RunStats
    written_count: int
    """Arêtes de CE run réellement écrites — pas « tentées »."""
    pending_count: int
    """Arêtes de CE run différées : leur cible n'est pas (encore) dans le corpus."""
    promoted_count: int
    """Pendantes de runs PASSÉS enfin résolues, parce que leur cible vient d'arriver."""

    reduced_count: int = 0
    """Arêtes éliminées par la réduction transitive — REDONDANTES, pas absentes.

    Une arête réduite n'est ni écrite ni pendante : le chemin la dit déjà. La compter
    à part est ce qui préserve la lisibilité de l'invariant
    ``written + pending == entrée (réduite)``."""


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

        # 0. La réduction transitive, à l'échelle du CORPUS — et ici seulement.
        #    L'extracteur ne voit qu'un document ; la hiérarchie d'un article se
        #    déclare des deux côtés à la fois (sa propre fermeture d'ancêtres, et
        #    l'arbre que déclarent les sections, dans D'AUTRES fichiers). Réduire par
        #    document était donc structurellement impossible. Ce service ne touche que
        #    la CONTENANCE : réduire une citation détruirait un fait.
        submitted = len(relations)
        relations = reduce_transitively(relations)
        reduced_count = submitted - len(relations)

        # 1. Écriture en batch. Ce qui ne s'écrit pas ressort — rien ne s'évapore.
        #    Chaque arête écrite est taguée du `run_id` (§8) : c'est ce qui la rend
        #    compensable à la maille du run (delete_relations_by_run), sans emporter
        #    les arêtes qu'un autre run a posées sur le même document.
        result = await self._graph_repo.upsert_relations(relations, context.run_id)

        # 2. Les trous sont une donnée : ils vont au cache, et on le DIT.
        if result.pending:
            await self._pending_repo.upsert_many(
                [
                    PendingRelation.from_relation(relation, context.run_id)
                    for relation in result.pending
                ]
            )
            for relation in result.pending:
                self._emit_relation(RELATION_PENDING, relation, context)
                stats = stats.with_count(RELATION_PENDING)

        if result.written:
            # `count` porte enfin les arêtes RÉUSSIES. Il portait auparavant les
            # relations tentées : un MATCH raté n'émettait rien, et la relation
            # disparaissait sans laisser de trace dans les compteurs.
            self._telemetry.emit(
                build_event(
                    event_type=RELATION_UPSERTED,
                    run_id=context.run_id,
                    owner_id=context.owner_id,
                    source=context.source,
                    payload={"count": len(result.written)},
                )
            )
            stats = stats.with_count(RELATION_UPSERTED)

        # 3. Rejeu ciblé : on ne retente QUE les pendantes dont la cible vient
        #    d'arriver. Le rejeu est borné par le delta du run, jamais par la taille
        #    du backlog — une pendante qui dort depuis 200 runs ne coûte rien.
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
        candidates = await self._pending_repo.promotable_for(
            written_node_ids, context.owner_id
        )
        if not candidates:
            return 0

        result = await self._graph_repo.upsert_relations(
            [candidate.to_relation() for candidate in candidates], context.run_id
        )

        if result.pending:
            # La cible vient pourtant d'être écrite : c'est donc la SOURCE qui
            # manque. On ne supprime pas — une pendante qu'on ne sait pas résoudre
            # reste une donnée vraie.
            self._telemetry.log(
                "warning",
                "relation.promotion.incomplete",
                count=len(result.pending),
            )

        written_keys = {PendingKey.from_relation(r) for r in result.written}
        promoted = [c for c in candidates if c.key in written_keys]

        await self._pending_repo.delete_many([c.key for c in promoted])
        for candidate in promoted:
            self._telemetry.emit(
                build_event(
                    event_type=RELATION_PROMOTED,
                    run_id=context.run_id,
                    owner_id=candidate.owner_id,
                    source=candidate.source,
                    document_id=candidate.source_id,
                    payload={
                        "target_id": candidate.target_id,
                        "relation_type": candidate.relation_type,
                        "first_seen_run": candidate.first_seen_run,
                    },
                )
            )
        return len(promoted)

    def _emit_relation(
        self, event_type: str, relation: Relation, context: PipelineContext
    ) -> None:
        self._telemetry.emit(
            build_event(
                event_type=event_type,
                run_id=context.run_id,
                owner_id=relation.owner_id,
                source=relation.source,
                document_id=relation.source_identifier.serialize(),
                payload={
                    "target_id": relation.target_identifier.serialize(),
                    "relation_type": relation.relation_type,
                },
            )
        )
