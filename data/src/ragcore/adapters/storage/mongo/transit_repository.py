"""Les relations en transit entre les deux phases d'un run (ADR-034 §4).

Une ligne par relation : la ``Relation`` sérialisée, et à plat les champs que la phase 2
filtre et que l'index couvre.
"""

from collections.abc import Sequence
from typing import Any

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.relation import Relation

__all__ = ["TRANSIT_RELATIONS_COLLECTION", "MongoTransitRelationRepository"]

TRANSIT_RELATIONS_COLLECTION = "transit_relations"
"""Dans la base de données, pas la méta."""

_RELATION_FIELD = "relation"


def _row(relation: Relation, run_id: RunId) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "relation_type": relation.relation_type,
        "source_id": relation.source_identifier.serialize(),
        "target_id": relation.target_identifier.serialize(),
        _RELATION_FIELD: relation.model_dump(mode="json"),
    }


class MongoTransitRelationRepository:
    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = TRANSIT_RELATIONS_COLLECTION,
    ) -> None:
        self._collection = client[db_name][collection]

    async def clear(self) -> None:
        await self._collection.delete_many({})

    async def insert_many(self, relations: Sequence[Relation], run_id: RunId) -> None:
        if not relations:
            return
        rows = [_row(relation, run_id) for relation in relations]
        await self._collection.insert_many(rows, ordered=False)

    async def delete_for_source(
        self, source_identifier: Identifier, run_id: RunId
    ) -> None:
        await self._collection.delete_many(
            {"run_id": run_id, "source_id": source_identifier.serialize()}
        )

    async def read_run(self, run_id: RunId) -> list[Relation]:
        cursor = self._collection.find({"run_id": run_id}, {_RELATION_FIELD: 1})
        return [Relation.model_validate(row[_RELATION_FIELD]) async for row in cursor]

    async def delete_run(self, run_id: RunId) -> None:
        await self._collection.delete_many({"run_id": run_id})

    async def count(self) -> int:
        return await self._collection.count_documents({})
