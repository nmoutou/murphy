"""Les relations non formatées (ADR-045) — accumulées de run en run, comme les pendantes.

Mêmes décisions que ``pending_repository`` :

1. **Union idempotente.** ``$setOnInsert`` fige ``first_seen_run``, ``$set`` fait
   avancer ``last_seen_run``. Revoir dix fois la même relation produit UNE entrée —
   c'est l'index unique sur la clé à quatre champs qui le garantit.

2. **Une compensation qui ne défait que son propre run.** Une ligne née d'un run
   précédent n'appartient pas à la saga qui échoue : ``delete_first_seen`` filtre sur
   ``first_seen_run``, jamais sur le seul ``source_id``.
"""

from collections.abc import Sequence

from pymongo import UpdateOne

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.unformatted_relation import UnformattedRelation

__all__ = ["UNFORMATTED_RELATIONS_COLLECTION", "MongoUnformattedRelationRepository"]

UNFORMATTED_RELATIONS_COLLECTION = "unformatted_relations"
"""La collection des relations non formatées, dans la base de données (MURPHY_DATA)."""


def _key_filter(relation: UnformattedRelation) -> dict[str, object]:
    """La clé à quatre champs — celle de l'index unique.

    ``sens`` en fait partie : « je cite X » et « X me cite » sont deux faits, et le
    ``$set`` écraserait sinon l'un par l'autre.
    """
    return {
        "source_id": relation.source_identifier.serialize(),
        "target_text": relation.target_text,
        "relation_type": relation.relation_type,
        "sens": relation.sens,
    }


def _upsert(relation: UnformattedRelation, run_id: RunId) -> UpdateOne:
    key = _key_filter(relation)
    return UpdateOne(
        key,
        {
            "$set": {
                **key,
                "source": relation.source.value,
                "metadata": dict(relation.metadata),
                "last_seen_run": run_id,
            },
            # first_seen_run est posé À LA CRÉATION uniquement : c'est ce qui
            # l'empêche de reculer quand la relation est revue.
            "$setOnInsert": {"first_seen_run": run_id},
        },
        upsert=True,
    )


class MongoUnformattedRelationRepository:
    """Implémentation Mongo de ``UnformattedRelationRepository``."""

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = UNFORMATTED_RELATIONS_COLLECTION,
    ) -> None:
        self._collection = client[db_name][collection]

    async def upsert_many(
        self, relations: Sequence[UnformattedRelation], run_id: RunId
    ) -> None:
        # Presque aucun document ne déclare de cible décrite : pas d'aller-retour Mongo
        # pour une liste vide.
        if not relations:
            return
        operations = [_upsert(relation, run_id) for relation in relations]
        await self._collection.bulk_write(operations, ordered=False)

    async def delete_first_seen(
        self, source_identifier: Identifier, run_id: RunId
    ) -> None:
        await self._collection.delete_many(
            {"source_id": source_identifier.serialize(), "first_seen_run": run_id}
        )

    async def count(self) -> int:
        return await self._collection.count_documents({})
