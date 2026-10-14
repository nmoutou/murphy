from collections.abc import AsyncIterator, Collection, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..models.identifiers import Identifier, RunId
from ..models.relation import Relation


@dataclass(frozen=True)
class TransitBatch:
    """Des lignes lues ensemble, et de quoi les supprimer une fois traitées."""

    row_ids: tuple[object, ...]
    """Opaques : seul le dépôt les comprend."""
    relations: tuple[Relation, ...]


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

    def pairs(
        self, run_id: RunId, relation_type: str
    ) -> AsyncIterator[tuple[str, str]]:
        """Les couples (source, cible) d'un verbe, en flux."""
        ...

    async def read_by_sources(
        self, run_id: RunId, relation_type: str, source_ids: Collection[str]
    ) -> list[Relation]: ...

    async def delete_by_sources(
        self, run_id: RunId, relation_type: str, source_ids: Collection[str]
    ) -> None: ...

    def batches_excluding(
        self, run_id: RunId, relation_types: Collection[str], size: int
    ) -> AsyncIterator[TransitBatch]:
        """Les lignes des autres verbes, par lots de ``size``. Supprimer un lot déjà
        rendu ne fait pas sauter de ligne."""
        ...

    async def delete_rows(self, batch: TransitBatch) -> None: ...

    async def count(self) -> int: ...
