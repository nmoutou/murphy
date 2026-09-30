from typing import Protocol, runtime_checkable

from ..models.pending import PendingKey, PendingRelation


@runtime_checkable
class PendingRelationRepository(Protocol):
    """Cache des relations pendantes (§13) — aucune relation n'est jamais jetée.

    Une pendante est une donnée *méta* (la santé de complétude du corpus), pas une
    donnée métier : elle vit à côté de l'audit et des bilans de run, pas dans le
    graphe. Ni TTL, ni compteur de tentatives — voir ``PendingRelation``.
    """

    async def upsert_many(self, pendings: list[PendingRelation]) -> None:
        """Union idempotente sur la clé (source_id, target_id, relation_type).

        Une pendante déjà connue voit son ``last_seen_run`` avancer ; son
        ``first_seen_run`` ne bouge jamais.
        """
        ...

    async def promotable_for(self, written_node_ids: set[str]) -> list[PendingRelation]:
        """Les pendantes dont la cible fait partie des nœuds écrits par CETTE run.

        C'est le rejeu *ciblé* : une pendante dont la cible n'est pas arrivée cette
        fois-ci ne peut pas se résoudre, et la retenter serait un coût pur qui croît
        avec le backlog. Le rejeu est borné par le delta de la run, jamais par
        l'historique.
        """
        ...

    async def delete_many(self, keys: list[PendingKey]) -> None:
        """Retire les pendantes enfin promues en arêtes réelles."""
        ...

    async def count(self) -> int:
        """Taille du backlog — un indicateur, pas une alarme.

        Aucun chemin de production ne la lit (le prod suit `pending_count`, le delta
        de la run, en mémoire). Elle est le point d'observation du backlog pour les
        tests d'intégration — contrat assumé, pas oubli.
        """
        ...
