"""Les relations en transit entre les deux phases d'un run (ADR-034 §4).

Une ligne par relation : la ``Relation`` sérialisée, et à plat les champs que la phase 2
filtre et que l'index couvre.
"""

from collections.abc import AsyncIterator, Collection, Iterator, Sequence
from typing import Any

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.relation import Relation
from ragcore.core.ports.transit_repository import TransitBatch

__all__ = ["TRANSIT_RELATIONS_COLLECTION", "MongoTransitRelationRepository"]

TRANSIT_RELATIONS_COLLECTION = "transit_relations"
"""Dans la base de données, pas la méta."""

_RELATION_FIELD = "relation"

_IN_CHUNK = 10_000
"""Les valeurs d'un ``$in`` : une requête Mongo ne dépasse pas 16 Mo."""

_PAIRS_BATCH = 10_000
"""Les couples rapatriés par aller-retour du curseur."""


def _row(relation: Relation, run_id: RunId) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "relation_type": relation.relation_type,
        "source_id": relation.source_identifier.serialize(),
        "target_id": relation.target_identifier.serialize(),
        _RELATION_FIELD: relation.model_dump(mode="json"),
    }


def _chunks(values: Collection[str]) -> Iterator[list[str]]:
    ordered = list(values)
    for start in range(0, len(ordered), _IN_CHUNK):
        yield ordered[start : start + _IN_CHUNK]


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

    async def pairs(
        self, run_id: RunId, relation_type: str
    ) -> AsyncIterator[tuple[str, str]]:
        cursor = self._collection.find(
            {"run_id": run_id, "relation_type": relation_type},
            {"_id": 0, "source_id": 1, "target_id": 1},
            batch_size=_PAIRS_BATCH,
        )
        async for row in cursor:
            yield row["source_id"], row["target_id"]

    async def read_by_sources(
        self, run_id: RunId, relation_type: str, source_ids: Collection[str]
    ) -> list[Relation]:
        relations: list[Relation] = []
        for chunk in _chunks(source_ids):
            cursor = self._collection.find(
                _by_sources(run_id, relation_type, chunk), {_RELATION_FIELD: 1}
            )
            relations.extend(
                [Relation.model_validate(row[_RELATION_FIELD]) async for row in cursor]
            )
        return relations

    async def delete_by_sources(
        self, run_id: RunId, relation_type: str, source_ids: Collection[str]
    ) -> None:
        for chunk in _chunks(source_ids):
            await self._collection.delete_many(
                _by_sources(run_id, relation_type, chunk)
            )

    async def batches_excluding(
        self, run_id: RunId, relation_types: Collection[str], size: int
    ) -> AsyncIterator[TransitBatch]:
        """Paginé sur ``_id`` croissant : une ligne supprimée derrière le curseur ne
        décale rien."""
        after: object | None = None
        while True:
            batch = await self._batch_after(run_id, relation_types, size, after)
            if not batch.row_ids:
                return
            yield batch
            after = batch.row_ids[-1]

    async def delete_rows(self, batch: TransitBatch) -> None:
        await self._collection.delete_many({"_id": {"$in": list(batch.row_ids)}})

    async def count(self) -> int:
        return await self._collection.count_documents({})

    async def _batch_after(
        self,
        run_id: RunId,
        relation_types: Collection[str],
        size: int,
        after: object | None,
    ) -> TransitBatch:
        query: dict[str, Any] = {
            "run_id": run_id,
            "relation_type": {"$nin": list(relation_types)},
        }
        if after is not None:
            query["_id"] = {"$gt": after}
        cursor = self._collection.find(query).sort("_id", 1).limit(size)
        rows = [row async for row in cursor]
        return TransitBatch(
            row_ids=tuple(row["_id"] for row in rows),
            relations=tuple(
                Relation.model_validate(row[_RELATION_FIELD]) for row in rows
            ),
        )


def _by_sources(
    run_id: RunId, relation_type: str, source_ids: list[str]
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "relation_type": relation_type,
        "source_id": {"$in": source_ids},
    }
