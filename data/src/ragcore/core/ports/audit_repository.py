from typing import Protocol, runtime_checkable

from ..models.audit import AuditEvent


@runtime_checkable
class AuditRepository(Protocol):
    """Journal d'audit append-only."""

    async def append(self, event: AuditEvent) -> None: ...
