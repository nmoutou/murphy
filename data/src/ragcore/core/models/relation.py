from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .document import SCHEMA_VERSION
from .enums import SourceName
from .identifiers import OwnerId, SourceIdentifier
from .verbs import ValidatedVerb


class Relation(BaseModel):
    """Relation entre deux documents (graphe de connaissance)."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = SCHEMA_VERSION
    source_identifier: SourceIdentifier  # document source de la relation
    target_identifier: SourceIdentifier  # document cible de la relation

    relation_type: ValidatedVerb
    """Le verbe de l'arête — une chaîne validée, plus un membre d'enum.

    Il **devient le type d'arête Neo4j** (``MERGE (a)-[r:$(verb)]->(b)``). Un verbe
    canonique (``cites``) et un mot brut non traduit (``zorglub``) y cohabitent
    légitimement : le second est un aveu, pas une erreur. Ce qui n'y entre jamais, c'est
    une chaîne qui ne peut pas être un type d'arête — d'où la validation.
    """

    owner_id: OwnerId
    source: SourceName  # source du document qui a déclaré cette relation
    metadata: dict[str, Any] = Field(default_factory=dict)
