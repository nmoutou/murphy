"""Les mesures de run, une par ``run_id``, dans la base méta."""

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.run_statistics import RunStatistics

__all__ = ["STATISTICS_COLLECTION", "MongoStatisticsRepository"]

STATISTICS_COLLECTION = "statistics"


class MongoStatisticsRepository:
    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = STATISTICS_COLLECTION,
    ) -> None:
        self._collection = client[db_name][collection]

    async def upsert(self, statistics: RunStatistics) -> None:
        await self._collection.replace_one(
            {"run_id": statistics.run_id}, statistics.to_document(), upsert=True
        )
