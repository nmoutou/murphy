from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..models.identifiers import Identifier, RunId
from ..models.unformatted_relation import UnformattedRelation


@runtime_checkable
class UnformattedRelationRepository(Protocol):
    """Les relations non formatées (ADR-045) : elles vivent avec les documents dont elles
    dérivent, et un nuke les efface avec eux.
    """

    async def upsert_many(
        self, relations: Sequence[UnformattedRelation], run_id: RunId
    ) -> None:
        """Union idempotente sur (source_id, target_text, relation_type, sens) : une
        relation connue voit son ``last_seen_run`` avancer, jamais son
        ``first_seen_run``.
        """
        ...

    async def delete_first_seen(
        self, source_identifier: Identifier, run_id: RunId
    ) -> None:
        """La compensation : seules les relations nées dans ce run sont retirées."""
        ...

    async def count(self) -> int:
        """Pour les tests d'intégration."""
        ...
