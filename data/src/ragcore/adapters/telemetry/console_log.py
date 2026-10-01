"""Les logs textuels de la télémétrie, vers le logging standard (`KEDRO_LOG_LEVEL`)."""

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
    def emit(self, event: AuditEvent) -> None:
        pass

    def log(self, level: str, message: str, **context: Any) -> None:
        log_level = _LEVEL_MAP.get(level, logging.INFO)
        if context:
            _LOGGER.log(log_level, message, extra=context)
        else:
            _LOGGER.log(log_level, message)
