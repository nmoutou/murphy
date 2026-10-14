from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..models.identifiers import Identifier, RunId
from ..models.relation import Relation


@runtime_checkable
class TransitRelationRepository(Protocol):
    """Les relations entre les deux phases d'un run (ADR-034 §4) : la phase 1 les
    écrit, la phase 2 les consomme. Temporaire : vide en dehors d'un run.
    """

    async def clear(self) -> None:
        """Au démarrage du run, avant la phase 1 : les restes d'un run en échec ne
        contiennent rien que le suivant ne reproduise."""
        ...

    async def insert_many(self, relations: Sequence[Relation], run_id: RunId) -> None:
        """Une ligne par relation, sans dédoublonnage : la réduction s'en charge."""
        ...

    async def delete_for_source(
        self, source_identifier: Identifier, run_id: RunId
    ) -> None:
        """La compensation : les lignes du document pour ce run."""
        ...

    async def read_run(self, run_id: RunId) -> list[Relation]: ...

    async def delete_run(self, run_id: RunId) -> None: ...

    async def count(self) -> int: ...
