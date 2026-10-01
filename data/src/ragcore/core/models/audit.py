from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, model_validator

from .enums import SourceName, TargetStore
from .identifiers import DocumentId, RunId

__all__ = ["AuditEvent", "build_event"]

_NO_DOCUMENT_ID_PREFIXES = ("pipeline.", "maintenance.")


class AuditEvent(BaseModel):
    """Append-only dans Mongo."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    event_type: str
    occurred_at: datetime
    run_id: RunId

    document_id: DocumentId | None
    source: SourceName | None
    target: TargetStore | None

    payload: dict[str, Any]
    success: bool
    error_message: str | None = None

    @model_validator(mode="after")
    def _validate_document_id_coherence(self) -> "AuditEvent":
        if (
            self.event_type.startswith(_NO_DOCUMENT_ID_PREFIXES)
            and self.document_id is not None
        ):
            raise ValueError(
                f"L'event '{self.event_type}' ne doit pas avoir de document_id"
            )
        return self


def build_event(  # noqa: PLR0913 — façade : exposer chaque champ de l'événement est son rôle
    event_type: str,
    run_id: RunId,
    *,
    document_id: DocumentId | None = None,
    source: SourceName | None = None,
    target: TargetStore | None = None,
    payload: dict[str, Any] | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        run_id=run_id,
        document_id=document_id,
        source=source,
        target=target,
        payload=payload or {},
        success=success,
        error_message=error_message,
    )
