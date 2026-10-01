from typing import Protocol, runtime_checkable

from ..models.pending import PendingKey, PendingRelation


@runtime_checkable
class PendingRelationRepository(Protocol):
    """Les relations pendantes : elles vivent avec les documents dont elles dérivent, et
    un nuke les efface avec eux.
    """

    async def upsert_many(self, pendings: list[PendingRelation]) -> None:
        """Union idempotente sur la clé : une pendante connue voit son ``last_seen_run``
        avancer, jamais son ``first_seen_run``.
        """
        ...

    async def promotable_for(self, written_node_ids: set[str]) -> list[PendingRelation]:
        """Les pendantes dont la cible fait partie des nœuds écrits par ce run : le rejeu
        est borné par le delta du run, jamais par l'historique.
        """
        ...

    async def delete_many(self, keys: list[PendingKey]) -> None: ...

    async def count(self) -> int:
        """Taille du backlog, pour les tests d'intégration : la production suit
        `pending_count`, en mémoire."""
        ...
