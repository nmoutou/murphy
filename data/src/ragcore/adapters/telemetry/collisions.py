"""Le détail des collisions, à côté de leurs comptes dans ``RunStats``."""

from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.run_collisions import RunCollisions

__all__ = ["CollisionsAggregator"]


class CollisionsAggregator:
    """Mutable, comme ``MeasuresAggregator`` : ``RunStats`` se recopie à chaque
    enregistrement, ce qui serait quadratique sur des dizaines de milliers de détails.
    """

    def __init__(self) -> None:
        self._records: list[CollisionRecord] = []

    def record(self, record: CollisionRecord) -> None:
        self._records.append(record)

    def snapshot(self) -> RunCollisions:
        return RunCollisions(tuple(self._records))
