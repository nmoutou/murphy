"""L'identité d'un run. Figée : c'est le seul objet que tous les workers partagent."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId

__all__ = ["PipelineContext"]


class PipelineContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: RunId
    sources: tuple[SourceName, ...] = ()
    """Telles que le plan les a résolues."""
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def source(self) -> SourceName | None:
        """La source des événements du run : la sienne s'il est mono-source, ``None``
        sinon. Un événement de document porte celle de son document."""
        return self.sources[0] if len(self.sources) == 1 else None

    @classmethod
    def create(cls, sources: tuple[SourceName, ...] = ()) -> "PipelineContext":
        """Le ``run_id`` est un hex nu, sans tiret."""
        return cls(
            run_id=RunId(uuid4().hex),
            sources=sources,
            started_at=datetime.now(UTC),
        )
