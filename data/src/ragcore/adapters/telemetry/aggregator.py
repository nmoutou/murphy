"""Agrégateur in-memory des AuditEvent — l'agrégat local d'UN worker.

Le ``threading.Lock`` d'avant a disparu, et pas par négligence : il protégeait un
``defaultdict`` mutable partagé. L'agrégat est désormais un ``RunStats`` immuable
que chaque ``emit`` remplace — il n'y a plus d'état à corrompre, donc plus rien à
verrouiller. C'est l'invariant 1 du pool (§11) appliqué ici : le verrou disparaît
par construction, pas par discipline.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED, DOCUMENT_PERSISTED

# Events dont on veut un breakdown par clé de payload.
_BREAKDOWN_KEY: dict[str, str] = {
    DOCUMENT_INVALIDATED: "reason",   # breakdown par raison de rejet
    DOCUMENT_PERSISTED: "operation",  # breakdown par opération (INSERT/UPDATE)
}


class RunStatsAggregator:
    """Agrège les AuditEvent en un ``RunStats``. Satisfait ``WorkerTelemetry``.

    ``snapshot()`` rend l'agrégat brut — c'est lui qu'on fusionne entre workers.
    ``finalize()`` y attache l'identité du run pour produire le ``RunSummary`` ;
    la persistance (fichier JSON + Mongo) reste à l'orchestrateur.
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
        self._stats = RunStats.empty()

    @property
    def counts(self) -> dict[str, int]:
        return dict(self._stats.counts)

    def emit(self, event: AuditEvent) -> None:
        stats = self._stats.with_count(event.event_type)
        payload_key = _BREAKDOWN_KEY.get(event.event_type)
        if payload_key is not None:
            value = (event.payload or {}).get(payload_key, "unknown")
            stats = stats.with_breakdown(event.event_type, value)
        self._stats = stats

    def log(self, level: str, message: str, **context: Any) -> None:  # noqa: ARG002
        return

    def record_unknown(self, category: str, value: str) -> None:
        """Un vocabulaire non reconnu se DÉCLARE — il ne se jette pas en silence."""
        self._stats = self._stats.with_unknown(category, value)

    def snapshot(self) -> RunStats:
        """L'agrégat local, à fusionner avec celui des autres workers."""
        return self._stats

    def close(self) -> None:
        """Rien à drainer : l'agrégat vit en mémoire."""
        return

    def finalize(
        self, status: RunStatus, error_message: str | None = None
    ) -> RunSummary:
        """Projette l'agrégat en RunSummary — l'identité s'attache ici, une fois."""
        return RunSummary.of(
            self._stats,
            context_run_id=self._run_id,
            owner_id=self._owner_id,
            source=self._source,
            started_at=self._started_at,
            status=RunStatus(status),
            error_message=error_message,
            ended_at=datetime.now(UTC),
        )
