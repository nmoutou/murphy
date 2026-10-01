"""Adaptateur de télémétrie qui implémente enfin .log().

Envoie les logs textuels vers le logger Python standard (niveau réglé par `KEDRO_LOG_LEVEL`).
"""

import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent

_LOGGER = logging.getLogger("ragcore.telemetry")

_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


class ConsoleLogTelemetry:
    """Implémente .log() vers le logging Python standard.

    .emit(event) est un no-op — les logs textuels et les audit events sont indépendants.
    """

    def emit(self, event: AuditEvent) -> None:
        """No-op : les audit events ne sont pas loggés ici."""
        pass

    def log(self, level: str, message: str, **context: Any) -> None:
        """Log un message textuel via le logger standard.

        Args:
            level: "debug" | "info" | "warning" | "error"
            message: Message texte
            **context: Contexte supplémentaire (logger.extra)
        """
        log_level = _LEVEL_MAP.get(level, logging.INFO)
        if context:
            _LOGGER.log(log_level, message, extra=context)
        else:
            _LOGGER.log(log_level, message)
