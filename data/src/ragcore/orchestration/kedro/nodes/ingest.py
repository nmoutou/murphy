"""Nœud de la phase 1 : lance ``IngestionRunner``. Son ``IngestionOutcome`` alimente la
phase 2, et cette arête du DAG est la barrière entre les deux.
"""

from __future__ import annotations

from ragcore.adapters.storage.opensearch.search_index import OpenSearchSearchIndex
from ragcore.application.ingestion_runner import (
    IngestionOutcome,
    IngestionRunner,
    WorkerResultsSink,
)
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import ParsedDocument
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.statistics_measures import STAGE_PHASE1
from ragcore.orchestration.kedro.stage_clock import StageClock

__all__ = ["ingest_node"]


def ingest_node(
    to_process: list[ParsedDocument],
    runner: IngestionRunner,
    search_index: OpenSearchSearchIndex,
    pipeline_context: PipelineContext,
    pipeline_runtime: AsyncRuntime,
    run_sink: WorkerResultsSink,
    stage_clock: StageClock,
) -> IngestionOutcome:
    """L'index n'est pas rafraîchi pendant l'écriture. ``finally`` : un run en échec ne
    doit pas laisser un index qui ne publie plus rien. Seul un run arrivé au bout est
    fusionné.

    Les agrégats des workers rejoignent ``run_sink`` ici, pas dans ``report`` : un run
    qui casse plus loin les garde dans son bilan et ses statistiques."""
    with stage_clock.stage(STAGE_PHASE1):
        pipeline_runtime.run(search_index.suspend_refresh())
        try:
            outcome = runner.run(to_process, pipeline_context, run_sink)
        finally:
            pipeline_runtime.run(search_index.resume_refresh())
        pipeline_runtime.run(search_index.force_merge())
    return outcome
