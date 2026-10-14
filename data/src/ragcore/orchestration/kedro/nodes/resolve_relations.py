"""Nœud de la phase 2 : il consomme l'``IngestionOutcome``, donc ne tourne qu'une fois
tous les nœuds du run écrits, et leurs relations en transit.

Non parallélisé : il traite l'union en un batch, sur le runtime du hook.
"""

from __future__ import annotations

from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import (
    ResolutionOutcome,
    ResolveRelationsService,
)
from ragcore.application.run_context import PipelineContext
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.statistics_measures import STAGE_PHASE2_WRITE
from ragcore.orchestration.kedro.stage_clock import StageClock

__all__ = ["resolve_relations_node"]


def resolve_relations_node(
    ingestion_outcome: IngestionOutcome,
    resolve_service: ResolveRelationsService,
    pipeline_runtime: AsyncRuntime,
    pipeline_context: PipelineContext,
    stage_clock: StageClock,
) -> ResolutionOutcome:
    with stage_clock.stage(STAGE_PHASE2_WRITE):
        return pipeline_runtime.run(
            resolve_service.execute(
                ingestion_outcome.written_node_ids, pipeline_context
            )
        )
