"""La session d'UN run : son état, ouvert en tête de run, clos en fin — sans ``None``.

Le hook Kedro vit le temps du process ; un run, lui, commence dans
``before_pipeline_run`` et finit dans ``after_pipeline_run`` ou ``on_pipeline_error``.
Tout ce qui n'existe que pendant ce run (contexte, télémétrie, agrégat, embedder)
est ici, et n'est jamais « pas encore posé » : une session existe
entière ou n'existe pas.
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
    """Monte la pile de télémétrie du run et l'agrégat qui fera son bilan."""
    aggregator = RunStatsAggregator(
        run_id=context.run_id,
        sources=context.sources,
        started_at=context.started_at,
    )
    telemetry = assemble_telemetry(aggregator)
    return telemetry, aggregator


@dataclass(frozen=True)
class RunSession:
    """L'état d'un run, et les deux gestes du hook sur lui : émettre, clore."""

    context: PipelineContext
    telemetry: TelemetryPort
    aggregator: RunStatsAggregator
    """L'agrégat du run. Le node `report` y POUSSE les stats des workers (il est le
    `run_stats_sink` du catalogue) ; `close` le finalise en bilan."""
    summaries: RunSummaryRepository
    embedder: BaseEmbedder
    """Gardé pour l'interroger en fin de run : un chunk qu'il a dû raccourcir pour tenir
    dans la fenêtre du modèle est un chunk dont la fin n'est PAS indexée. Le document est
    sauvé, le run est complet — mais le bilan doit le dire."""
    runtime: AsyncRuntime
    """Le runtime du hook : la session s'en sert, le hook le ferme."""

    def close(self, status: RunStatus, error_message: str | None = None) -> RunSummary:
        """Clôt le run, qu'il ait réussi ou cassé : l'ORDRE est tout l'enjeu.

        1. Les chunks que l'embedder a dû raccourcir. Le compteur vit sur l'embedder (il
           est le seul à voir le refus du service) et il est lu ICI, une fois, après tous
           les workers. Déclarés AUSSI sur un run cassé : le raccourcissement a bien eu
           lieu, et il pointe une config à corriger. Émis AVANT le bilan, pour qu'il y
           figure.
        2. Le bilan, dont le statut se dérive des compteurs — dont ceux que le node
           `report` a poussés depuis les workers.

        Rend le bilan persisté.
        """
        self._declare_truncations()
        return self._persist_summary(status, error_message)

    def _declare_truncations(self) -> None:
        """Un chunk raccourci n'est pas une perte, mais ce n'est pas rien : il se DÉCLARE.

        Le document est ingéré (donc l'équation de complétude tombe juste, à raison), mais
        la fin du chunk n'est pas indexée. Un compteur non nul veut dire une seule chose :
        **le `CHUNKING_MAX_CHARS` configuré n'est pas compatible avec la fenêtre du modèle**. Le
        run est sauvé ; la configuration, elle, est à corriger.
        """
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
        """Finalise l'agrégat et persiste le RunSummary dans Mongo.

        Le statut annoncé n'est **pas** celui qui sort (``finalize`` le re-dérive des
        compteurs). Qui veut savoir si le run est vraiment `ok` doit lire le bilan, pas
        ce qu'il a demandé.
        """
        summary = self.aggregator.finalize(status=status, error_message=error_message)
        self.runtime.run(self.summaries.upsert(summary))
        return summary
