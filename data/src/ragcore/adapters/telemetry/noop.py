"""Télémétrie qui n'écrit nulle part."""

from typing import Any

from ragcore.core.models.audit import AuditEvent


class NoopTelemetry:
    """Désactive un backend sans rendre les sites d'émission conditionnels."""

    def emit(self, event: AuditEvent) -> None:
        return

    def log(self, level: str, message: str, **context: Any) -> None:
        return
