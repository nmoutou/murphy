from datetime import datetime
from typing import Protocol, runtime_checkable

from ..models.identifiers import RunId
from ..models.run_collisions import RunCollisions


@runtime_checkable
class CollisionRepository(Protocol):
    """Un document par source en collision et par run, en parties s'il le faut :
    rejouer un run remplace les siens."""

    async def replace_run(
        self, run_id: RunId, started_at: datetime, collisions: RunCollisions
    ) -> None: ...
