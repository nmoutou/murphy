from typing import Protocol, runtime_checkable

from ..models.run_statistics import RunStatistics


@runtime_checkable
class StatisticsRepository(Protocol):
    """Un document par run, clé ``run_id`` : rejouer un run le remplace."""

    async def upsert(self, statistics: RunStatistics) -> None: ...
