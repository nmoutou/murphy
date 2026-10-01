"""La télémétrie observe l'ingestion, elle ne la fait jamais échouer.

Un backend qui lève — à l'émission ou à la fermeture — est isolé : il ne casse ni
l'ingestion, ni les autres backends. Ces tests provoquent l'échec, c'est leur seule
raison d'être : le chemin nominal, où rien ne rate, ne prouve rien de l'isolement.
"""

from datetime import UTC, datetime
from typing import Any

from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.adapters.telemetry.worker_backends import WorkerBackends
from ragcore.adapters.telemetry.worker_stack import WorkerTelemetryStack
from ragcore.core.models.audit import AuditEvent, build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED

RUN = RunId("r-1")


class ExplodingAggregator(RunStatsAggregator):
    """Un agrégat qui refuse l'événement."""

    def emit(self, event: AuditEvent) -> None:
        raise RuntimeError("l'agrégat refuse l'événement")


class ExplodingLog:
    """Un backend de log qui refuse de se fermer."""

    def emit(self, event: AuditEvent) -> None:
        return

    def log(self, level: str, message: str, **context: Any) -> None:
        return

    def close(self) -> None:
        raise RuntimeError("le backend refuse de se fermer")


def _telemetry(aggregate: RunStatsAggregator) -> WorkerTelemetryStack:
    return WorkerTelemetryStack(WorkerBackends(log=ExplodingLog(), aggregate=aggregate))


def _aggregator(cls: type[RunStatsAggregator] = RunStatsAggregator) -> Any:
    return cls(run_id=RUN, sources=(SourceName.LEGI,), started_at=datetime.now(UTC))


def test_a_backend_that_raises_does_not_fail_the_ingestion() -> None:
    telemetry = _telemetry(_aggregator(ExplodingAggregator))
    telemetry.emit(build_event(DOCUMENT_PERSISTED, RUN))  # ne lève pas — l'assertion


def test_a_backend_that_fails_to_close_does_not_stop_the_others() -> None:
    telemetry = _telemetry(_aggregator())

    telemetry.close()  # ne lève pas — l'assertion


def test_the_aggregate_is_closed_last() -> None:
    """L'agrégat rend le bilan : il doit survivre aux autres backends."""
    backends = WorkerBackends(log=ExplodingLog(), aggregate=_aggregator())

    names = [name for name, _ in backends.closable_in_order()]

    assert names[-1] == "aggregate"
