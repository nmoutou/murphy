from typing import Protocol, runtime_checkable

from ..models.identifiers import RunId
from ..models.run_summary import RunSummary


@runtime_checkable
class RunSummaryRepository(Protocol):
    """Un bilan par run, clé ``run_id`` : rejouer un run le remplace."""

    async def upsert(self, summary: RunSummary) -> None: ...

    async def get(self, run_id: RunId) -> RunSummary | None: ...
