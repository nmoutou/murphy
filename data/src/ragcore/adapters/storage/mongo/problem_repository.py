"""Le détail des problèmes d'un run, dans ``MURPHY_PROBLEMS`` : une collection par sorte
de problème, une ligne par problème (ADR-036)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.problems import Problem

__all__ = ["COLLISIONS_COLLECTION", "INSERT_BATCH_SIZE", "MongoProblemRepository"]

COLLISIONS_COLLECTION = "collisions"
INSERT_BATCH_SIZE = 1_000

_Row = dict[str, Any]


class MongoProblemRepository:
    def __init__(self, client: MongoClient, db_name: str) -> None:
        self._database = client[db_name]

    async def insert_run(self, run_id: RunId, problems: Sequence[Problem]) -> None:
        for collection, rows in _rows_by_collection(run_id, problems).items():
            for start in range(0, len(rows), INSERT_BATCH_SIZE):
                batch = rows[start : start + INSERT_BATCH_SIZE]
                await self._database[collection].insert_many(batch)


def _rows_by_collection(
    run_id: RunId, problems: Sequence[Problem]
) -> dict[str, list[_Row]]:
    grouped: dict[str, list[_Row]] = {}
    for problem in problems:
        collection, row = _routed(problem)
        grouped.setdefault(collection, []).append({"run_id": run_id, **row})
    return grouped


def _routed(problem: Problem) -> tuple[str, _Row]:
    return COLLISIONS_COLLECTION, _collision_row(problem)


def _collision_row(record: CollisionRecord) -> _Row:
    return {
        "source": record.source.value,
        "reason": record.reason,
        "identifier": record.identifier,
        "key": record.key,
        "files": list(record.files),
    }
