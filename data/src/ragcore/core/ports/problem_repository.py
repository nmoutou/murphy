from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..models.identifiers import RunId
from ..models.problems import Problem


@runtime_checkable
class ProblemRepository(Protocol):
    """Une ligne par problème, sous le ``run_id`` du run qui l'a rencontré."""

    async def insert_run(self, run_id: RunId, problems: Sequence[Problem]) -> None: ...
