"""Adaptateur de télémétrie qui dispatche selon un registry par event_type.

Implémente le port TelemetryPort avec un routage granulaire.
"""

import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.services.telemetry_registry import TelemetryRegistry

_LOGGER = logging.getLogger(__name__)


class RegistryAwareTelemetry:
    """Fan-out guidé par un TelemetryRegistry.
    
    Dispatche chaque emit() vers les 4 backends selon le behavior_for(event_type).
    Les exceptions des delegates sont isolées (best-effort).
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
