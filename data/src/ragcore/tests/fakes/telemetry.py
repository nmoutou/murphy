"""Télémétrie enregistreuse, une par worker : rien de partagé, donc aucun verrou."""

from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.unknown_tally import UnknownExample
from ragcore.core.ports.runtime import AsyncRuntime


class RecordingTelemetry:
    def __init__(self, worker_id: int = 0) -> None:
        self.worker_id = worker_id
        self.events: list[AuditEvent] = []
        self.logs: list[tuple[str, str]] = []
        self.closed = False
        self._declared = RunStats.empty()

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def log(self, level: str, message: str, **context: Any) -> None:
        del context
        self.logs.append((level, message))

    def record_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> None:
        self._declared = self._declared.with_unknown(category, value, example)

    def record_collision(self, key: str, source_files: tuple[str, ...]) -> None:
        self._declared = self._declared.with_collision(key, source_files)

    def snapshot(self) -> RunStats:
        stats = self._declared
        for event in self.events:
            stats = stats.with_count(event.event_type)
        return stats

    def events_of(self, event_type: str) -> list[AuditEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def close(self) -> None:
        self.closed = True


class RecordingTelemetryFactory:
    def __init__(self) -> None:
        self.built: list[RecordingTelemetry] = []

    def build(self, worker_id: int, runtime: AsyncRuntime) -> RecordingTelemetry:
        del runtime
        telemetry = RecordingTelemetry(worker_id)
        self.built.append(telemetry)
        return telemetry
