"""La pile de télémétrie d'un worker : la console pour les logs, l'agrégat pour les
événements."""

import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.run_measures import MeasurePath, RunMeasures
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.unknown_tally import UnknownExample

from .worker_backends import WorkerBackends

_LOGGER = logging.getLogger(__name__)


class WorkerTelemetryStack:
    """Satisfait ``WorkerTelemetry``.

    Une exception de backend est journalisée, jamais propagée : la télémétrie ne fait
    pas échouer l'ingestion. Un compteur de document perdu se voit quand même, le run
    sort ``degraded``.
    """

    def __init__(self, backends: WorkerBackends) -> None:
        self._backends = backends

    def emit(self, event: AuditEvent) -> None:
        try:
            self._backends.aggregate.emit(event)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un backend en panne ne casse pas le run, l'échec est journalisé
            _LOGGER.warning(
                "telemetry backend 'aggregate' error on %s: %s", event.event_type, exc
            )

    def log(self, level: str, message: str, **context: Any) -> None:
        try:
            self._backends.log.log(level, message, **context)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un log textuel perdu ne fausse aucun compteur, il ne casse pas le run
            _LOGGER.warning("telemetry backend 'log' error on log(): %s", exc)

    def record_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> None:
        """Droit à l'agrégat : un inconnu n'est pas un événement d'audit."""
        self._backends.aggregate.record_unknown(category, value, example)

    def record_collision(self, record: CollisionRecord) -> None:
        self._backends.aggregate.record_collision(record.reason)
        self._backends.problems.record(record)

    def record_invalidation(self, reason: str) -> None:
        self._backends.aggregate.record_invalidation(reason)

    def record_measure(self, path: MeasurePath, value: float, ref: str) -> None:
        self._backends.measures.record(path, value, ref)

    def snapshot(self) -> RunStats:
        return self._backends.aggregate.snapshot()

    def snapshot_measures(self) -> RunMeasures:
        return self._backends.measures.snapshot()

    def close(self) -> None:
        """Un backend qui échoue à se fermer n'empêche pas les suivants ; l'échec est
        journalisé."""
        for name, backend in self._backends.closable_in_order():
            closer = getattr(backend, "close", None)
            if closer is None:
                continue
            try:
                closer()
            except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un close() raté ne doit pas empêcher de fermer les backends suivants ; l'échec est journalisé
                _LOGGER.warning(
                    "telemetry backend '%s' error on close(): %s", name, exc
                )
