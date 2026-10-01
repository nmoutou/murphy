"""Adaptateur de télémétrie qui dispatche selon un registry par event_type.

Implémente le port TelemetryPort avec un routage granulaire.
"""

import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.run_stats import RunStats
from ragcore.core.services.telemetry_registry import TelemetryRegistry

from .worker_backends import WorkerBackends

_LOGGER = logging.getLogger(__name__)


class RegistryAwareTelemetry:
    """Fan-out guidé par un TelemetryRegistry — la pile de télémétrie d'UN worker.

    Dispatche chaque emit() vers ses backends selon le behavior_for(event_type).
    Les exceptions des delegates sont isolées (best-effort) : la télémétrie observe
    l'ingestion, elle ne la fait jamais échouer. Isolées, mais journalisées : un backend
    qui rate se lit dans les logs. Et si c'est l'agrégat qui perd un compteur de
    document, l'équation de complétude le voit — le run sort ``degraded``.

    Satisfait ``WorkerTelemetry`` : au-delà du fan-out, elle sait rendre son agrégat
    local (``snapshot``) et fermer ses backends (``close``). Sans cela le pool ne
    pourrait pas la consommer — un fan-out qui ne sait pas se réduire n'est pas une
    pile de worker, c'est un tuyau.

    Les backends sont un ``WorkerBackends`` typé (§12) : plus de clés-chaînes, plus
    de garde ``isinstance`` sur l'agrégat — chaque rôle est un champ, et ``aggregate``
    EST un ``RunStatsAggregator`` par construction.
    """

    def __init__(
        self,
        registry: TelemetryRegistry,
        backends: WorkerBackends,
    ):
        """
        Args:
            registry: TelemetryRegistry qui map event_type → EventBehavior
            backends: WorkerBackends — les rôles (log/aggregate) wirés en amont. ``aggregate`` porte le RunStats que snapshot() rend au pool.
        """
        self._registry = registry
        self._backends = backends

    def emit(self, event: AuditEvent) -> None:
        """Dispatche vers les backends selon le EventBehavior.

        Le `event_type` est préservé tel quel — le registry contrôle le routage,
        pas le contenu. L'appariement est un pour un avec les champs du behavior :
        ``log``→``log``, ``aggregate``→``aggregate``.

        Un backend qui lève ne fait pas tomber les autres, et ne fait pas tomber
        l'ingestion (cf. ``_deliver``).
        """
        behavior = self._registry.behavior_for(event.event_type)

        if behavior.log:
            self._deliver("log", self._backends.log, event)
        if behavior.aggregate:
            self._deliver("aggregate", self._backends.aggregate, event)

    def _deliver(self, name: str, backend: Any, event: AuditEvent) -> None:
        """Un backend, une livraison, et un échec qui se DIT.

        L'isolement des exceptions n'est pas négociable : la télémétrie observe
        l'ingestion, elle ne la fait jamais échouer.
        """
        try:
            backend.emit(event)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un backend en panne ne casse pas le run, l'échec est journalisé
            _LOGGER.warning(
                "telemetry backend '%s' error on %s: %s", name, event.event_type, exc
            )

    def log(self, level: str, message: str, **context: Any) -> None:
        """Passe-plat vers le backend log.

        .log() n'est pas filtré par le registry — toujours émis.
        """
        try:
            self._backends.log.log(level, message, **context)
        except Exception as exc:  # noqa: BLE001 — frontière de télémétrie : un log textuel perdu ne fausse aucun compteur, il ne casse pas le run
            _LOGGER.warning("telemetry backend 'log' error on log(): %s", exc)

    def record_unknown(self, category: str, value: str) -> None:
        """Un vocabulaire non reconnu se déclare — il ne se jette pas en silence.

        Va droit à l'agrégat : un inconnu n'est pas un événement d'audit, c'est un
        aveu d'ignorance que le bilan du run doit porter (``RunStats.unknowns``).
        """
        self._backends.aggregate.record_unknown(category, value)

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
