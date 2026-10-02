from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import SourceName
from .identifiers import Identifier
from .verbs import ValidatedVerb


class Relation(BaseModel):
    """Relation entre deux documents (graphe de connaissance)."""

    model_config = ConfigDict(frozen=True)

    source_identifier: Identifier
    target_identifier: Identifier

    relation_type: ValidatedVerb
    """Devient le type d'arête Neo4j. Un verbe canonique (``cite``) et un mot brut non
    traduit y cohabitent ; la validation écarte ce qui ne peut pas être un type d'arête.
    """

    source: SourceName  # la source qui a déclaré la relation
    metadata: dict[str, Any] = Field(default_factory=dict)
