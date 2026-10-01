"""Une arête différée : sa cible n'est pas (encore) dans le corpus.

Écrite en phase 2, rejouée le jour où la cible arrive. Elle peut rester pendante
indéfiniment : un arrêt qui cite une directive jamais ingérée n'est pas une erreur.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import SourceName
from .identifiers import DocumentId, Identifier, RunId
from .relation import Relation
from .verbs import ValidatedVerb

__all__ = ["PendingKey", "PendingRelation"]


class PendingKey(BaseModel):
    """Clé d'unicité d'une pendante."""

    model_config = ConfigDict(frozen=True)

    source_id: DocumentId
    target_id: DocumentId
    relation_type: ValidatedVerb

    @classmethod
    def from_relation(cls, relation: Relation) -> "PendingKey":
        """La pendante et la relation qui la résout portent la même clé : c'est ce qui
        permet de dire « cette pendante vient d'être écrite ».
        """
        return cls(
            source_id=relation.source_identifier.serialize(),
            target_id=relation.target_identifier.serialize(),
            relation_type=relation.relation_type,
        )


class PendingRelation(BaseModel):
    """Relation dont la cible n'existait pas au moment de l'écriture.

    Ni TTL ni ``retry_count`` : le rejeu ne vise que les pendantes dont la cible vient
    d'arriver, donc une pendante n'est jamais « essayée puis échouée ».
    """

    model_config = ConfigDict(frozen=True)

    source_id: DocumentId
    target_id: DocumentId
    relation_type: ValidatedVerb
    source: SourceName
    metadata: dict[str, Any] = Field(default_factory=dict)

    first_seen_run: RunId
    last_seen_run: RunId

    @property
    def key(self) -> PendingKey:
        return PendingKey(
            source_id=self.source_id,
            target_id=self.target_id,
            relation_type=self.relation_type,
        )

    @classmethod
    def from_relation(cls, relation: Relation, run_id: RunId) -> "PendingRelation":
        return cls(
            source_id=relation.source_identifier.serialize(),
            target_id=relation.target_identifier.serialize(),
            relation_type=relation.relation_type,
            source=relation.source,
            metadata=dict(relation.metadata),
            first_seen_run=run_id,
            last_seen_run=run_id,
        )

    def to_relation(self) -> Relation:
        return Relation(
            source_identifier=Identifier(raw=self.source_id),
            target_identifier=Identifier(raw=self.target_id),
            relation_type=self.relation_type,
            source=self.source,
            metadata=dict(self.metadata),
        )
