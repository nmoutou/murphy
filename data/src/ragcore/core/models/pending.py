"""PendingRelation — une arête différée est une DONNÉE, pas un vide (§13).

En phase 2, une relation dont le ``MATCH (b)`` échoue n'est pas perdue : sa cible
n'est simplement pas (encore) dans le corpus. Elle est écrite ici et rejouée le
jour où la cible arrive. Une pendante peut rester pendante indéfiniment — un
arrêt qui cite une directive jamais ingérée produit un lien légitime vers
l'extérieur, pas une erreur.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import SourceName
from .identifiers import DocumentId, Identifier, RunId
from .relation import Relation
from .verbs import ValidatedVerb

__all__ = ["PendingKey", "PendingRelation"]


class PendingKey(BaseModel):
    """Clé d'unicité d'une pendante : (source_id, target_id, relation_type)."""

    model_config = ConfigDict(frozen=True)

    source_id: DocumentId  # identifiant sérialisé
    target_id: DocumentId  # identifiant sérialisé
    relation_type: ValidatedVerb

    @classmethod
    def from_relation(cls, relation: Relation) -> "PendingKey":
        """La clé d'une relation RÉSOLUE — la même identité qu'une pendante.

        Une pendante et la relation qui la résout portent la MÊME clé : c'est ce qui
        permet de dire « cette pendante vient d'être écrite ». Recomposer un tuple à la
        main aux deux endroits (ce que faisait ``_key_tuple``) laissait les deux formes
        diverger en silence — l'unicité est un fait du modèle, elle vit ici.
        """
        return cls(
            source_id=relation.source_identifier.serialize(),
            target_id=relation.target_identifier.serialize(),
            relation_type=relation.relation_type,
        )


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
        """Reconstruit la relation d'origine pour la rejouer."""
        return Relation(
            source_identifier=Identifier(raw=self.source_id),
            target_identifier=Identifier(raw=self.target_id),
            relation_type=self.relation_type,
            source=self.source,
            metadata=dict(self.metadata),
        )
