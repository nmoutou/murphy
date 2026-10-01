"""Ce qui n'existe que pendant un run, ouvert dans ``before_pipeline_run`` et clos dans
``after_pipeline_run`` ou ``on_pipeline_error``. Une session existe entière ou pas du
tout : jamais de ``None``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ragcore.adapters.telemetry import RunStatsAggregator
from ragcore.adapters.telemetry.factory import assemble_telemetry
from ragcore.adapters.telemetry.worker_stack import WorkerTelemetryStack
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.run_summary_repository import RunSummaryRepository
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import CHUNK_TRUNCATED
from ragcore.orchestration.kedro.assembly import ReportsTruncations

__all__ = ["RunSession", "start_telemetry"]

logger = logging.getLogger(__name__)


def start_telemetry(
    context: PipelineContext,
) -> tuple[WorkerTelemetryStack, RunStatsAggregator]:
    aggregator = RunStatsAggregator(
        run_id=context.run_id,
        sources=context.sources,
        started_at=context.started_at,
    )
    telemetry = assemble_telemetry(aggregator)
    return telemetry, aggregator


@dataclass(frozen=True)
class RunSession:
    context: PipelineContext
    telemetry: TelemetryPort
    aggregator: RunStatsAggregator
    """Le `run_stats_sink` du catalogue : `report` y pousse les stats des workers."""
    summaries: RunSummaryRepository
    embedder: BaseEmbedder
    """Interrogé en fin de run sur les chunks qu'il a dû raccourcir."""
    runtime: AsyncRuntime
    """Celui du hook, qui le ferme."""

    def close(self, status: RunStatus, error_message: str | None = None) -> RunSummary:
        """Rend le bilan persisté, que le run ait réussi ou cassé. Les chunks raccourcis
        sont déclarés avant, pour y figurer."""
        self._declare_truncations()
        return self._persist_summary(status, error_message)

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
        summary = self.aggregator.finalize(status=status, error_message=error_message)
        self.runtime.run(self.summaries.upsert(summary))
        return summary
