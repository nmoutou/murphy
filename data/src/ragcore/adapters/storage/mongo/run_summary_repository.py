"""Les bilans de run, un par ``run_id``. Un champ vide n'est pas écrit."""

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_summary import RunSummary

__all__ = ["MongoRunSummaryRepository"]


class MongoRunSummaryRepository:
    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = "run_summaries",
    ) -> None:
        self._collection = client[db_name][collection]

    async def upsert(self, summary: RunSummary) -> None:
        await self._collection.replace_one(
            {"run_id": summary.run_id},
            summary.model_dump(mode="json", exclude_none=True),
            upsert=True,
        )

    async def get(self, run_id: RunId) -> RunSummary | None:
        doc = await self._collection.find_one({"run_id": run_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RunSummary.model_validate(doc)
