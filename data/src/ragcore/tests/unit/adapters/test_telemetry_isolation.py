"""La télémétrie observe l'ingestion, elle ne la fait jamais échouer.

Un backend qui lève — à l'émission ou à la fermeture — est isolé : il ne casse ni
l'ingestion, ni les autres backends. Ces tests provoquent l'échec, c'est leur seule
raison d'être : le chemin nominal, où rien ne rate, ne prouve rien de l'isolement.
"""

from datetime import UTC, datetime
from typing import Any

from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.adapters.telemetry.registry_aware import RegistryAwareTelemetry
from ragcore.adapters.telemetry.worker_backends import WorkerBackends
from ragcore.core.models.audit import AuditEvent, build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.services.telemetry_registry import EventBehavior, TelemetryRegistry
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED

RUN = RunId("r-1")


class ExplodingBackend:
    """Un backend qui refuse d'écrire, ou de se fermer."""

    def __init__(self, *, on_emit: bool = True, on_close: bool = False) -> None:
        self._on_emit = on_emit
        self._on_close = on_close

    def emit(self, event: AuditEvent) -> None:
        if self._on_emit:
            raise RuntimeError("le backend refuse l'événement")

    def log(self, level: str, message: str, **context: Any) -> None:
        return

    def close(self) -> None:
        if self._on_close:
            raise RuntimeError("le backend refuse de se fermer")


def _telemetry(log_backend: ExplodingBackend) -> RegistryAwareTelemetry:
    registry = TelemetryRegistry.from_catalog(
        {DOCUMENT_PERSISTED: EventBehavior(level="info", log=True, aggregate=True)}
    )
    return RegistryAwareTelemetry(
        registry=registry,
        backends=WorkerBackends(
            log=log_backend,
            aggregate=RunStatsAggregator(
                run_id=RUN,
                sources=(SourceName.LEGI,),
                started_at=datetime.now(UTC),
            ),
        ),
    )


def test_a_backend_that_raises_does_not_fail_the_ingestion() -> None:
    telemetry = _telemetry(ExplodingBackend())
    telemetry.emit(build_event(DOCUMENT_PERSISTED, RUN))  # ne lève pas — l'assertion


def test_the_aggregate_still_receives_the_event() -> None:
    """Un backend qui tombe n'emporte pas l'agrégat : le compteur reste juste."""
    telemetry = _telemetry(ExplodingBackend())

    telemetry.emit(build_event(DOCUMENT_PERSISTED, RUN))

    assert telemetry.snapshot().counts[DOCUMENT_PERSISTED] == 1


def test_a_backend_that_fails_to_close_does_not_stop_the_others() -> None:
    telemetry = _telemetry(ExplodingBackend(on_emit=False, on_close=True))

    telemetry.close()  # ne lève pas — l'assertion


def test_the_aggregate_is_closed_last() -> None:
    """L'agrégat rend le bilan : il doit survivre aux autres backends."""
    backends = WorkerBackends(
        log=ExplodingBackend(),
        aggregate=RunStatsAggregator(RUN, (SourceName.LEGI,), datetime.now(UTC)),
    )

    names = [name for name, _ in backends.closable_in_order()]

    assert names[-1] == "aggregate"
