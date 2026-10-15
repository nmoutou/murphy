"""Télémétrie enregistreuse, une par worker : rien de partagé, donc aucun verrou."""

from typing import Any

from ragcore.adapters.telemetry.measures import MeasuresAggregator
from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.problems import FileProblem, InvalidatedDocument
from ragcore.core.models.run_measures import MeasurePath, RunMeasures
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.unknown_tally import UnknownExample
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.telemetry_events import collision_count_key, invalidation_count_key


class RecordingTelemetry:
    def __init__(self, worker_id: int = 0) -> None:
        self.worker_id = worker_id
        self.events: list[AuditEvent] = []
        self.logs: list[tuple[str, str]] = []
        self.closed = False
        self._declared = RunStats.empty()
        self.measured: list[tuple[MeasurePath, float, str]] = []
        self.collisions: list[CollisionRecord] = []
        self.problems: list[FileProblem] = []
        self.invalidated: list[InvalidatedDocument] = []

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def log(self, level: str, message: str, **context: Any) -> None:
        del context
        self.logs.append((level, message))

    def record_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> None:
        self._declared = self._declared.with_unknown(category, value, example)

    def record_collision(self, record: CollisionRecord) -> None:
        self._declared = self._declared.with_count(collision_count_key(record.reason))
        self.collisions.append(record)

    def record_problem(self, problem: FileProblem) -> None:
        self.problems.append(problem)

    def record_invalidation(self, document: InvalidatedDocument) -> None:
        self._declared = self._declared.with_count(
            invalidation_count_key(document.reason)
        )
        self.invalidated.append(document)

    def snapshot(self) -> RunStats:
        stats = self._declared
        for event in self.events:
            stats = stats.with_count(event.event_type)
        return stats

    def record_measure(self, path: MeasurePath, value: float, ref: str) -> None:
        self.measured.append((path, value, ref))

    def snapshot_measures(self) -> RunMeasures:
        aggregator = MeasuresAggregator()
        for path, value, ref in self.measured:
            aggregator.record(path, value, ref)
        return aggregator.snapshot()

    def values_of(self, path: MeasurePath) -> list[float]:
        return [value for measured, value, _ in self.measured if measured == path]

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
