"""Les relations non formatées (ADR-045), accumulées de run en run comme les pendantes.

La compensation filtre sur ``first_seen_run``, jamais sur le seul ``source_id`` : une
ligne née d'un run précédent n'appartient pas à la saga qui échoue.
"""

from collections.abc import Sequence

from pymongo import UpdateOne

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.unformatted_relation import UnformattedRelation

__all__ = ["UNFORMATTED_RELATIONS_COLLECTION", "MongoUnformattedRelationRepository"]

UNFORMATTED_RELATIONS_COLLECTION = "unformatted_relations"
"""Dans la base de données, pas la méta."""


def _key_filter(relation: UnformattedRelation) -> dict[str, object]:
    """Celle de l'index unique. ``sens`` en fait partie : « je cite X » et « X me cite »
    sont deux faits."""
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
                "last_seen_run": run_id,
            },
            # Seulement à la création : first_seen_run ne doit pas reculer
            "$setOnInsert": {"first_seen_run": run_id},
        },
        upsert=True,
    )


class MongoUnformattedRelationRepository:
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
