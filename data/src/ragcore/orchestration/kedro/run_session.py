"""Ce qui n'existe que pendant un run, ouvert dans ``before_pipeline_run`` et clos dans
``after_pipeline_run`` ou ``on_pipeline_error``. Une session existe entière ou pas du
tout : jamais de ``None``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from ragcore.adapters.telemetry import MeasuresAggregator, RunStatsAggregator
from ragcore.adapters.telemetry.factory import assemble_telemetry
from ragcore.adapters.telemetry.worker_stack import WorkerTelemetryStack
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import FULL_RATIO, SourceInventory
from ragcore.core.models.run_measures import RunMeasures
from ragcore.core.models.run_statistics import RunStatistics
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.run_summary_repository import RunSummaryRepository
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.statistics_repository import StatisticsRepository
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.telemetry_events import CHUNK_TRUNCATED
from ragcore.orchestration.kedro.assembly import ReportsTruncations
from ragcore.orchestration.kedro.stage_clock import StageClock

__all__ = ["RunAggregates", "RunSession", "start_telemetry"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunAggregates:
    """Ce que le run accumule : les compteurs du bilan, les mesures et les étapes de
    ``statistics``. Le ``run_sink`` du catalogue : ``ingest`` y pousse les agrégats des
    workers."""

    stats: RunStatsAggregator
    measures: MeasuresAggregator
    stages: StageClock

    def absorb(self, stats: RunStats, measures: RunMeasures) -> None:
        self.stats.absorb(stats)
        self.measures.absorb(measures)

    def record_inventories(
        self, inventories: Mapping[SourceName, SourceInventory]
    ) -> None:
        self.stats.record_inventories(inventories)


def start_telemetry(
    context: PipelineContext, ingestion_ratio: float = FULL_RATIO
) -> tuple[WorkerTelemetryStack, RunAggregates]:
    aggregates = RunAggregates(
        stats=RunStatsAggregator(
            run_id=context.run_id,
            sources=context.sources,
            started_at=context.started_at,
            ingestion_ratio=ingestion_ratio,
        ),
        measures=MeasuresAggregator(),
        stages=StageClock(),
    )
    telemetry = assemble_telemetry(aggregates.stats, aggregates.measures)
    return telemetry, aggregates


@dataclass(frozen=True)
class RunSession:
    context: PipelineContext
    telemetry: WorkerTelemetry
    aggregates: RunAggregates
    summaries: RunSummaryRepository
    statistics: StatisticsRepository
    embedder: BaseEmbedder
    """Interrogé en fin de run sur les chunks qu'il a dû raccourcir."""
    runtime: AsyncRuntime
    """Celui du hook, qui le ferme."""

    def close(self, status: RunStatus, error_message: str | None = None) -> RunSummary:
        """Rend le bilan persisté, que le run ait réussi ou cassé, et persiste ses
        statistiques. Les chunks raccourcis sont déclarés avant, pour y figurer."""
        self._declare_truncations()
        summary = self._persist_summary(status, error_message)
        self.runtime.run(self.statistics.upsert(self._statistics()))
        return summary

    def _declare_truncations(self) -> None:
        """Non nul : `CHUNKING_MAX_CHARS` est incompatible avec la fenêtre du modèle."""
        if not isinstance(self.embedder, ReportsTruncations):
            return
        truncations = self.embedder.truncations
        if not truncations:
            return
        self.telemetry.emit(
            build_event(
                event_type=CHUNK_TRUNCATED,
                run_id=self.context.run_id,
                source=self.context.source,
                payload={"count": truncations},
            )
        )
        logger.warning(
            "%d chunk(s) raccourci(s) pour tenir dans la fenêtre du modèle. Le corpus est "
            "complet, mais la fin de ces chunks n'est pas indexée : baisser `CHUNKING_MAX_CHARS`.",
            truncations,
        )

    def _persist_summary(
        self, status: RunStatus, error_message: str | None
    ) -> RunSummary:
        """Le statut sorti peut différer de l'annoncé : ``finalize`` le re-dérive des
        compteurs."""
        summary = self.aggregates.stats.finalize(
            status=status, error_message=error_message
        )
        self.runtime.run(self.summaries.upsert(summary))
        return summary

    def _statistics(self) -> RunStatistics:
        return RunStatistics(
            run_id=self.context.run_id,
            started_at=self.context.started_at,
            stages_s=self.aggregates.stages.durations(),
            measures=self.aggregates.measures.snapshot(),
        )
