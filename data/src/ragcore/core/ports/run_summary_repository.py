from typing import Protocol, runtime_checkable

from ..models.identifiers import RunId
from ..models.run_summary import RunSummary


@runtime_checkable
class RunSummaryRepository(Protocol):
    """Persistance des bilans de run — un par run, jamais fusionné.

    ``upsert`` et non ``append`` : un run n'a qu'un seul bilan, et le rejouer doit
    le remplacer, pas en empiler un second. La clé est le ``run_id`` — c'est
    précisément l'identité que ``RunStats`` n'a pas, et que ``RunSummary`` attache
    après la réduction.
    """

    async def upsert(self, summary: RunSummary) -> None: ...

    async def get(self, run_id: RunId) -> RunSummary | None: ...
