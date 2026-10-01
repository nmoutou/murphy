"""Télémétrie enregistreuse — un backend par worker, sans aucun verrou.

Aucune section critique ici, et ce n'est pas un raccourci de test : c'est le point.
Chaque worker a SA pile ; rien n'est partagé, donc rien n'est à protéger.
"""

from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.run_stats import RunStats
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.telemetry_events import AUDIT_WRITE_FAILED


class RecordingTelemetry:
    def __init__(self, worker_id: int = 0) -> None:
        self.worker_id = worker_id
        self.events: list[AuditEvent] = []
        self.logs: list[tuple[str, str]] = []
        self.closed = False
        self._unknowns: dict[str, list[str]] = {}
        self._audit_failures = 0

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def log(self, level: str, message: str, **context: Any) -> None:
        del context
        self.logs.append((level, message))

    def record_unknown(self, category: str, value: str) -> None:
        known = self._unknowns.setdefault(category, [])
        if value not in known:
            known.append(value)

    def record_audit_failure(self, n: int = 1) -> None:
        """Comme le vrai : le compte va à l'agrégat, il n'est PAS réémis en event.

        Le distinguer de ``events`` n'est pas cosmétique — c'est ce qui fait qu'un test
        de non-récursion a du sens : si l'implémentation réelle réémettait, elle
        apparaîtrait ici dans ``events``, et le fake mentirait en la laissant passer.
        """
        self._audit_failures += n

    def snapshot(self) -> RunStats:
        stats = RunStats.empty()
        for event in self.events:
            stats = stats.with_count(event.event_type)
        for category, values in self._unknowns.items():
            for value in values:
                stats = stats.with_unknown(category, value)
        # Les échecs d'audit voyagent par le MÊME monoïde que le reste — sans quoi ils
        # resteraient dans le worker et n'atteindraient jamais le bilan du run.
        if self._audit_failures:
            stats = stats.with_count(AUDIT_WRITE_FAILED, self._audit_failures)
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
