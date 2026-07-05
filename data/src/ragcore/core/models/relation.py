from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .document import SCHEMA_VERSION
from .enums import RelationType, SourceName
from .identifiers import OwnerId, SourceIdentifier


class Relation(BaseModel):
    """Relation entre deux documents (graphe de connaissance)."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = SCHEMA_VERSION
    source_identifier: SourceIdentifier  # document source de la relation
    target_identifier: SourceIdentifier  # document cible de la relation
    relation_type: RelationType
    owner_id: OwnerId
    source: SourceName  # source du document qui a déclaré cette relation
    metadata: dict[str, Any] = Field(default_factory=dict)
