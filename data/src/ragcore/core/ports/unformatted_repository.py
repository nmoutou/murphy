from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..models.identifiers import Identifier, RunId
from ..models.unformatted_relation import UnformattedRelation


@runtime_checkable
class UnformattedRelationRepository(Protocol):
    """Les relations non formatées (ADR-045) — accumulées, jamais jetées.

    Une relation non formatée attend sa résolution comme une pendante attend sa cible :
    elle vit avec les documents dont elle dérive, et un nuke l'efface avec eux.
    """

    async def upsert_many(
        self, relations: Sequence[UnformattedRelation], run_id: RunId
    ) -> None:
        """Union idempotente sur la clé (source_id, target_text, relation_type, sens).

        Une relation déjà connue voit son ``last_seen_run`` avancer ; son
        ``first_seen_run`` ne bouge jamais.
        """
        ...

    async def delete_first_seen(
        self, source_identifier: Identifier, run_id: RunId
    ) -> None:
        """Retire les relations de ce document NÉES dans ce run — la compensation.

        Celles d'un run précédent restent : la saga ne défait que ce qu'elle a créé.
        """
        ...

    async def count(self) -> int:
        """Taille de la collection — le point d'observation des tests d'intégration."""
        ...
