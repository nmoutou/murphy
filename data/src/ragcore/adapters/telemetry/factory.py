"""Une pile de télémétrie par worker : aucun objet partagé, donc aucun verrou."""

from datetime import datetime

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.ports.runtime import AsyncRuntime

from .aggregator import RunStatsAggregator
from .console_log import ConsoleLogTelemetry
from .worker_backends import WorkerBackends
from .worker_stack import WorkerTelemetryStack

__all__ = ["WorkerTelemetryFactory", "assemble_telemetry"]


def assemble_telemetry(aggregate: RunStatsAggregator) -> WorkerTelemetryStack:
    """Partagé par la fabrique et le hook : un backend ajouté se voit en un seul
    point."""
    return WorkerTelemetryStack(
        WorkerBackends(log=ConsoleLogTelemetry(), aggregate=aggregate)
    )


class WorkerTelemetryFactory:
    def __init__(
        self,
        run_id: RunId,
        sources: tuple[SourceName, ...],
        started_at: datetime,
    ) -> None:
        self._run_id = run_id
        self._sources = sources
        self._started_at = started_at

    def build(self, worker_id: int, runtime: AsyncRuntime) -> WorkerTelemetryStack:
        del (
            worker_id,
            runtime,
        )  # la pile vit en mémoire : ni boucle ni identité requises
        aggregator = RunStatsAggregator(
            run_id=self._run_id,
            sources=self._sources,
            started_at=self._started_at,
        )
        return assemble_telemetry(aggregator)
