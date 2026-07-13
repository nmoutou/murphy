"""PendingRelation — une arête différée est une DONNÉE, pas un vide (§13).

En phase 2, une relation dont le ``MATCH (b)`` échoue n'est pas perdue : sa cible
n'est simplement pas (encore) dans le corpus. Elle est écrite ici et rejouée le
jour où la cible arrive. Une pendante peut rester pendante indéfiniment — un
arrêt qui cite une directive jamais ingérée produit un lien légitime vers
l'extérieur, pas une erreur.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .document import SCHEMA_VERSION
from .enums import SourceName
from .identifiers import OwnerId, RunId, deserialize_identifier
from .relation import Relation
from .verbs import ValidatedVerb

__all__ = ["PendingKey", "PendingRelation"]


class PendingKey(BaseModel):
    """Clé d'unicité d'une pendante : (owner_id, source_id, target_id, relation_type).

    ``owner_id`` est dans la clé SANS EXCEPTION. Une pendante n'est pas un fait du
    monde : c'est un trou dans un graphe *donné*. « Cet arrêt cite cette directive »
    est universel ; « cette arête me manque » est relatif au propriétaire du graphe.
    Sans owner_id, promouvoir la pendante d'un propriétaire effacerait celle d'un
    autre — dont l'arête ne serait jamais écrite, et rien ne le signalerait.
    """

    model_config = ConfigDict(frozen=True)

    owner_id: OwnerId
    source_id: str  # identifiant sérialisé
    target_id: str  # identifiant sérialisé
    relation_type: ValidatedVerb


class PendingRelation(BaseModel):
    """Relation dont la cible n'existait pas au moment de l'écriture.

    Ni TTL, ni ``retry_count`` : avec un rejeu ciblé (on ne retente que les
    pendantes dont la cible vient d'arriver), une pendante n'est jamais « essayée
    puis échouée ». Elle est écrite une fois, puis promue une fois — ou jamais.
    Un compteur de tentatives compterait un événement qui ne se produit pas ; les
    deux estampilles de run, elles, disent quelque chose de réel sur la
    persistance du lien dans le corpus.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: int = SCHEMA_VERSION

    owner_id: OwnerId
    source_id: str
    target_id: str
    relation_type: ValidatedVerb
    source: SourceName
    metadata: dict[str, Any] = Field(default_factory=dict)

    first_seen_run: RunId
    last_seen_run: RunId

    @property
    def key(self) -> PendingKey:
        return PendingKey(
            owner_id=self.owner_id,
            source_id=self.source_id,
            target_id=self.target_id,
            relation_type=self.relation_type,
        )

    @classmethod
    def from_relation(cls, relation: Relation, run_id: RunId) -> "PendingRelation":
        return cls(
            owner_id=relation.owner_id,
            source_id=relation.source_identifier.serialize(),
            target_id=relation.target_identifier.serialize(),
            relation_type=relation.relation_type,
            source=relation.source,
            metadata=dict(relation.metadata),
            first_seen_run=run_id,
            last_seen_run=run_id,
        )

    def to_relation(self) -> Relation:
        """Reconstruit la relation d'origine pour la rejouer."""
        return Relation(
            source_identifier=deserialize_identifier(self.source_id),
            target_identifier=deserialize_identifier(self.target_id),
            relation_type=self.relation_type,
            owner_id=self.owner_id,
            source=self.source,
            metadata=dict(self.metadata),
        )
