"""PipelineContext — l'identité d'un run, immuable et partageable sans risque.

Frozen, et ce n'est pas cosmétique : le contexte est le seul objet que *tous* les
workers voient (invariant 1 du pool, §11). S'il était mutable, il redeviendrait
exactement le genre d'état partagé qu'un verrou doit protéger.
"""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId

__all__ = ["PipelineContext"]


class PipelineContext(BaseModel):
    """run_id, sources, started_at — ce qui identifie un run."""

    model_config = ConfigDict(frozen=True)

    run_id: RunId
    sources: tuple[SourceName, ...] = ()
    """Les sources que le run ingère, telles que le plan les a résolues."""
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def source(self) -> SourceName | None:
        """La source qu'estampillent les événements du run : la sienne s'il est
        mono-source, ``None`` sinon. Un événement de document porte, lui, la source de
        son document."""
        return self.sources[0] if len(self.sources) == 1 else None

    @classmethod
    def create(cls, sources: tuple[SourceName, ...] = ()) -> "PipelineContext":
        """Ouvre un run neuf : identifiant tiré, horloge démarrée.

        Le ``run_id`` est un hex nu, sans tiret : la clé du run dans l'audit et le
        bilan Mongo.
        """
        return cls(
            run_id=RunId(uuid4().hex),
            sources=sources,
            started_at=datetime.now(UTC),
        )
