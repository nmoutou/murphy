"""Le détail des problèmes d'un run, dans ``MURPHY_PROBLEMS`` : une collection par sorte
de problème, une ligne par problème (ADR-036)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.problems import CopyStamp, Problem, SupersededCopy

__all__ = [
    "COLLISIONS_COLLECTION",
    "INSERT_BATCH_SIZE",
    "SUPERSEDED_COLLECTION",
    "MongoProblemRepository",
]

COLLISIONS_COLLECTION = "collisions"
SUPERSEDED_COLLECTION = "superseded"
INSERT_BATCH_SIZE = 1_000
_NS_PER_S = 1_000_000_000

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
    match problem:
        case CollisionRecord():
            return COLLISIONS_COLLECTION, _collision_row(problem)
        case SupersededCopy():
            return SUPERSEDED_COLLECTION, _superseded_row(problem)


def _collision_row(record: CollisionRecord) -> _Row:
    return {
        "source": record.source.value,
        "reason": record.reason,
        "identifier": record.identifier,
        "key": record.key,
        "files": list(record.files),
    }


def _superseded_row(copy: SupersededCopy) -> _Row:
    return {
        "source": copy.source.value,
        "identifier": copy.identifier,
        "root": copy.root,
        "kept": _stamp_row(copy.kept),
        "discarded": _stamp_row(copy.discarded),
    }


def _stamp_row(stamp: CopyStamp) -> _Row:
    """Une date Mongo, à la milliseconde : la ligne sert à dater, l'arbitrage a déjà
    comparé les nanosecondes."""
    return {
        "path": stamp.path,
        "mtime": datetime.fromtimestamp(stamp.mtime_ns / _NS_PER_S, tz=UTC),
    }
