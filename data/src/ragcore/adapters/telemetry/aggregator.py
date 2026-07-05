"""Agrégateur in-memory des AuditEvent ; produit un RunSummary sur finalize()."""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED, DOCUMENT_PERSISTED

_LOGGER = logging.getLogger(__name__)

# Events dont on veut un breakdown par clé de payload
_BREAKDOWN_KEY: dict[str, str] = {
    DOCUMENT_INVALIDATED: "reason",   # breakdown par raison de rejet
    DOCUMENT_PERSISTED: "operation",  # breakdown par opération (INSERT/UPDATE)
}


class RunStatsAggregator:
    """Agrégateur in-memory des AuditEvent d'un run.

    Implémente TelemetryPort pour être branché via RegistryAwareTelemetry.
    `finalize()` construit et retourne le RunSummary ; la persistance
    (fichier JSON + Mongo) est de la responsabilité de l'orchestrateur (TelemetryHooks).
    """

    def __init__(
        self,
        run_id: RunId,
        owner_id: OwnerId,
        source: SourceName | None,
        started_at: datetime,
    ) -> None:
        self._run_id = run_id
        self._owner_id = owner_id
        self._source = source
        self._started_at = started_at
        self._lock = threading.Lock()

        self._counts: dict[str, int] = defaultdict(int)
        self._by_reason: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    @property
    def counts(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def emit(self, event: AuditEvent) -> None:
        with self._lock:
            self._counts[event.event_type] += 1
            payload_key = _BREAKDOWN_KEY.get(event.event_type)
            if payload_key is not None:
                value = (event.payload or {}).get(payload_key, "unknown")
                self._by_reason[event.event_type][value] += 1

    def log(self, level: str, message: str, **context: Any) -> None:  # noqa: ARG002
        return

    def finalize(self, status: RunStatus, error_message: str | None = None) -> RunSummary:
        """Construit et retourne le RunSummary agrégé.

        La persistance (fichier JSON local + upsert Mongo) est gérée par l'appelant.
        """
        ended_at = datetime.now(timezone.utc)
        with self._lock:
            counts_snapshot = dict(self._counts)
            summaries: dict[str, dict[str, Any]] = {
                event_type: {"by_reason": dict(reasons)}
                for event_type, reasons in self._by_reason.items()
            }

        return RunSummary(
            run_id=self._run_id,
            owner_id=self._owner_id,
            source=self._source,
            status=status,
            started_at=self._started_at,
            ended_at=ended_at,
            counts=counts_snapshot,
            summaries=summaries,
            error_message=error_message,
        )

