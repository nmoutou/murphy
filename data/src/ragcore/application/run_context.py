"""PipelineContext — l'identité d'un run, immuable et partageable sans risque.

Frozen, et ce n'est pas cosmétique : le contexte est le seul objet que *tous* les
workers voient (invariant 1 du pool, §11). S'il était mutable, il redeviendrait
exactement le genre d'état partagé qu'un verrou doit protéger.
"""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId

__all__ = ["PipelineContext"]


class PipelineContext(BaseModel):
    """run_id, owner_id, source, started_at — ce qui identifie un run."""

    model_config = ConfigDict(frozen=True)

    run_id: RunId
    owner_id: OwnerId
    source: SourceName | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls, owner_id: OwnerId, source: SourceName | None = None
    ) -> "PipelineContext":
        """Ouvre un run neuf : identifiant tiré, horloge démarrée.

        Le ``run_id`` est un hex nu, sans tiret : il est repris tel quel dans les
        noms de fichiers de télémétrie (``{iso}_{run_id}.jsonl``), donc il doit
        traverser un système de fichiers sans se faire échapper.
        """
        return cls(
            run_id=RunId(uuid4().hex),
            owner_id=owner_id,
            source=source,
            started_at=datetime.now(UTC),
        )
