"""La pile de télémétrie d'UN worker : la console pour les logs, l'agrégat pour les
événements."""

import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.unknown_tally import UnknownExample

from .worker_backends import WorkerBackends

_LOGGER = logging.getLogger(__name__)


class WorkerTelemetryStack:
    """La pile de télémétrie d'UN worker.

    Chaque ``emit()`` va à l'agrégat. Une exception de backend est isolée
    (best-effort) : la télémétrie observe l'ingestion, elle ne la fait jamais échouer.
    Isolée, mais journalisée. Et si l'agrégat perd un compteur de document, l'équation
    de complétude le voit — le run sort ``degraded``.

    Satisfait ``WorkerTelemetry`` : elle sait rendre son agrégat local (``snapshot``)
    et fermer ses backends (``close``).

    Les backends sont un ``WorkerBackends`` typé (§12) : chaque rôle est un champ, et
    ``aggregate`` EST un ``RunStatsAggregator`` par construction.
    """

    def __init__(self, backends: WorkerBackends) -> None:
        self._backends = backends

    def emit(self, event: AuditEvent) -> None:
        """Compte l'événement dans l'agrégat — sans jamais faire échouer l'appelant."""
        try:
            self._backends.aggregate.emit(event)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un backend en panne ne casse pas le run, l'échec est journalisé
            _LOGGER.warning(
                "telemetry backend 'aggregate' error on %s: %s", event.event_type, exc
            )

    def log(self, level: str, message: str, **context: Any) -> None:
        """Passe-plat vers le backend log."""
        try:
            self._backends.log.log(level, message, **context)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un log textuel perdu ne fausse aucun compteur, il ne casse pas le run
            _LOGGER.warning("telemetry backend 'log' error on log(): %s", exc)

    def record_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> None:
        """Un vocabulaire non reconnu se déclare — il ne se jette pas en silence.

        Va droit à l'agrégat : un inconnu n'est pas un événement d'audit, c'est un
        aveu d'ignorance que le bilan du run doit porter (``RunStats.unknowns``).
        """
        self._backends.aggregate.record_unknown(category, value, example)

    def snapshot(self) -> RunStats:
        """L'agrégat local de ce worker, à fusionner avec celui des autres."""
        return self._backends.aggregate.snapshot()

    def close(self) -> None:
        """Ferme les backends de ce worker. Un backend qui refuse de mourir ne doit
        pas empêcher les autres de le faire — mais il ne meurt pas en silence.

        L'ordre compte : l'agrégat est fermé **en dernier** (``closable_in_order``).
        """
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
