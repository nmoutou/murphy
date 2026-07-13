"""Persistance des bilans de run.

``upsert`` sur ``run_id`` : un run n'a qu'un bilan. Rejouer un run doit remplacer
son bilan, pas en empiler un second — sinon « combien de runs ont tourné ? »
n'a plus de réponse.
"""

from motor.motor_asyncio import AsyncIOMotorClient

from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_summary import RunSummary

__all__ = ["MongoRunSummaryRepository"]


class MongoRunSummaryRepository:
    """Implémentation Mongo de ``RunSummaryRepository``."""

    def __init__(
        self,
        client: AsyncIOMotorClient,
        db_name: str,
        collection: str = "meta_run_summaries",
    ) -> None:
        self._collection = client[db_name][collection]

    async def upsert(self, summary: RunSummary) -> None:
        await self._collection.replace_one(
            {"run_id": summary.run_id},
            summary.model_dump(mode="json"),
            upsert=True,
        )

    async def get(self, run_id: RunId) -> RunSummary | None:
        doc = await self._collection.find_one({"run_id": run_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return RunSummary.model_validate(doc)
