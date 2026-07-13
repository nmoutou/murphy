"""Adaptateur de télémétrie qui dispatche selon un registry par event_type.

Implémente le port TelemetryPort avec un routage granulaire.
"""

import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.run_stats import RunStats
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.services.telemetry_registry import TelemetryRegistry

from .aggregator import RunStatsAggregator

_LOGGER = logging.getLogger(__name__)


class RegistryAwareTelemetry:
    """Fan-out guidé par un TelemetryRegistry — la pile de télémétrie d'UN worker.

    Dispatche chaque emit() vers les 4 backends selon le behavior_for(event_type).
    Les exceptions des delegates sont isolées (best-effort) : la télémétrie observe
    l'ingestion, elle ne la fait jamais échouer.

    Satisfait ``WorkerTelemetry`` : au-delà du fan-out, elle sait rendre son agrégat
    local (``snapshot``) et fermer ses backends (``close``). Sans cela le pool ne
    pourrait pas la consommer — un fan-out qui ne sait pas se réduire n'est pas une
    pile de worker, c'est un tuyau.
    """

    def __init__(
        self,
        registry: TelemetryRegistry,
        backends: dict[str, TelemetryPort],
    ):
        """
        Args:
            registry: TelemetryRegistry qui map event_type → EventBehavior
            backends: Dict des backends wired en amont.
                Clés attendues : "log", "jsonl", "mongo", "aggregate"
                Le backend "aggregate" DOIT être un RunStatsAggregator : c'est lui
                qui porte le RunStats que snapshot() rend au pool.
        """
        self._registry = registry
        self._backends = backends

    def emit(self, event: AuditEvent) -> None:
        """Dispatche vers les backends selon le EventBehavior.
        
        Le `event_type` est préservé tel quel — le registry contrôle le routage,
        pas le contenu.
        """
        behavior = self._registry.behavior_for(event.event_type)

        if behavior.log:
            try:
                self._backends["log"].emit(event)
            except Exception as exc:
                _LOGGER.warning("telemetry backend 'log' error on %s: %s", event.event_type, exc)

        if behavior.track_jsonl:
            try:
                self._backends["jsonl"].emit(event)
            except Exception as exc:
                _LOGGER.warning("telemetry backend 'jsonl' error on %s: %s", event.event_type, exc)

        if behavior.track_mongo:
            try:
                self._backends["mongo"].emit(event)
            except Exception as exc:
                _LOGGER.warning("telemetry backend 'mongo' error on %s: %s", event.event_type, exc)

        if behavior.aggregate:
            try:
                self._backends["aggregate"].emit(event)
            except Exception as exc:
                _LOGGER.warning("telemetry backend 'aggregate' error on %s: %s", event.event_type, exc)

    def log(self, level: str, message: str, **context: Any) -> None:
        """Passe-plat vers le backend log.

        .log() n'est pas filtré par le registry — toujours émis.
        """
        try:
            self._backends["log"].log(level, message, **context)
        except Exception as exc:
            _LOGGER.warning("telemetry backend 'log' error on log(): %s", exc)

    def record_unknown(self, category: str, value: str) -> None:
        """Un vocabulaire non reconnu se déclare — il ne se jette pas en silence.

        Va droit à l'agrégat : un inconnu n'est pas un événement d'audit, c'est un
        aveu d'ignorance que le bilan du run doit porter (``RunStats.unknowns``).
        """
        aggregate = self._backends.get("aggregate")
        if isinstance(aggregate, RunStatsAggregator):
            aggregate.record_unknown(category, value)

    def snapshot(self) -> RunStats:
        """L'agrégat local de ce worker, à fusionner avec celui des autres."""
        aggregate = self._backends.get("aggregate")
        if isinstance(aggregate, RunStatsAggregator):
            return aggregate.snapshot()
        return RunStats.empty()

    def close(self) -> None:
        """Ferme les backends de ce worker. Un backend qui refuse de mourir ne doit
        pas empêcher les autres de le faire.
        """
        for name, backend in self._backends.items():
            closer = getattr(backend, "close", None)
            if closer is None:
                continue
            try:
                closer()
            except Exception as exc:
                _LOGGER.warning("telemetry backend '%s' error on close(): %s", name, exc)
