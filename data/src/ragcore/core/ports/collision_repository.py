from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..models.collision import Collision
from ..models.identifiers import RunId


@runtime_checkable
class CollisionRepository(Protocol):
    """Le détail des collisions du DERNIER run (ADR-049) — un échafaudage d'analyse.

    ``replace`` et non ``append`` : la collection décrit le run en cours, pas
    l'historique, que les bilans portent déjà. Lève ``CollisionRecordingError`` si
    l'écriture échoue : le bilan et la collection ne concorderaient plus.
    """

    async def replace(self, run_id: RunId, collisions: Sequence[Collision]) -> None: ...
