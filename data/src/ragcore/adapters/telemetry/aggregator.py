"""L'agrégat local d'un worker : un ``RunStats`` immuable que chaque ``emit`` remplace,
donc rien à verrouiller.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.models.unknown_tally import UnknownExample
from ragcore.core.services.unknown_categories import UNKNOWN_CATEGORIES
from ragcore.core.telemetry_events import COUNT_CARRYING_EVENTS, PAYLOAD_COUNT_KEY

_EVERY_CATEGORY = RunStats(
    counts={}, unknowns={category: {} for category in UNKNOWN_CATEGORIES}
)
"""Neutre pour la fusion, mais fait exister chaque catégorie : un bilan sans inconnu dit
``"roots": {}`` plutôt que de perdre la clé (ADR-048)."""


def _weight_of(event_type: str, payload: dict[str, Any]) -> int:
    """Combien de choses l'événement rapporte : 1, sauf pour ceux de
    ``COUNT_CARRYING_EVENTS``. Un ``count`` non entier vaut 1 : un payload n'est pas un
    contrat typé, et il ne doit pas faire tomber le bilan.
    """
    if event_type not in COUNT_CARRYING_EVENTS:
        return 1
    count = payload.get(PAYLOAD_COUNT_KEY)
    return count if isinstance(count, int) and count >= 0 else 1


class RunStatsAggregator:
    """Satisfait ``WorkerTelemetry``. ``finalize()`` produit le ``RunSummary`` ; sa
    persistance reste à l'orchestrateur.
    """

    def __init__(
        self,
        run_id: RunId,
        sources: tuple[SourceName, ...],
        started_at: datetime,
    ) -> None:
        self._run_id = run_id
        self._sources = sources
        self._started_at = started_at
        self._stats = RunStats.empty()

    @property
    def counts(self) -> dict[str, int]:
        return dict(self._stats.counts)

    def emit(self, event: AuditEvent) -> None:
        weight = _weight_of(event.event_type, event.payload or {})
        # TODO : pas de compteurs par source, un run multi-source ne dit pas chez qui.
        # Ce serait un axe de plus sur `RunStats`, pas ici.
        self._stats = self._stats.with_count(event.event_type, weight)

    def log(self, level: str, message: str, **context: Any) -> None:  # noqa: ARG002
        return

    def record_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> None:
        self._stats = self._stats.with_unknown(category, value, example)

    def record_collision(self, key: str, source_files: tuple[str, ...]) -> None:
        """Rangée en liste ou refusée, une clé en collision se compte."""
        self._stats = self._stats.with_collision(key, source_files)

    def snapshot(self) -> RunStats:
        return self._stats

    def absorb(self, stats: RunStats) -> None:
        """Fusionne l'agrégat des workers : sans lui, l'agrégateur du hook ne verrait
        pas les échecs survenus dans les workers. L'ordre est indifférent."""
        self._stats = self._stats.merge(stats)

    def close(self) -> None:
        """L'agrégat vit en mémoire."""
        return

    def finalize(
        self, status: RunStatus, error_message: str | None = None
    ) -> RunSummary:
        return RunSummary.of(
            self._stats.merge(_EVERY_CATEGORY),
            context_run_id=self._run_id,
            sources=self._sources,
            started_at=self._started_at,
            status=RunStatus(status),
            error_message=error_message,
            ended_at=datetime.now(UTC),
        )
