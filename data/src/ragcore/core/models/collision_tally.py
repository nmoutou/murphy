"""Ce que le bilan sait d'une clé en collision : combien de documents, et où la voir.

Un document compte une fois (ADR-049). La fusion reste commutative (cf. ``RunStats``) :
l'exemple gardé est le plus petit, jamais « le premier vu », qui dépendrait de l'ordre
de fin des workers.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["CollisionTally"]


class CollisionTally(BaseModel):
    model_config = ConfigDict(frozen=True)

    count: int
    example: tuple[str, ...]
    """Les fichiers d'un document, distincts, dans l'ordre des facettes de la table."""

    @classmethod
    def seen_in(cls, source_files: tuple[str, ...]) -> "CollisionTally":
        return cls(count=1, example=source_files)

    def merge(self, other: "CollisionTally") -> "CollisionTally":
        """Associatif et commutatif."""
        return CollisionTally(
            count=self.count + other.count, example=min(self.example, other.example)
        )
