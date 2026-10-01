"""Ce que le bilan sait d'un mot inconnu : combien de documents, et où le voir.

Un document compte une fois, quel que soit le nombre d'occurrences. La fusion reste
commutative (cf. ``RunStats``) : l'exemple gardé est le plus petit, jamais « le premier
vu », qui dépendrait de l'ordre de fin des workers.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["UnknownExample", "UnknownTally"]


class UnknownExample(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: str
    source_file: str
    """Vide quand le document n'a pas de fichier source connu."""

    def sort_key(self) -> tuple[str, str]:
        return (self.identifier, self.source_file)


class UnknownTally(BaseModel):
    model_config = ConfigDict(frozen=True)

    count: int
    example: UnknownExample

    @classmethod
    def seen_in(cls, example: UnknownExample) -> "UnknownTally":
        return cls(count=1, example=example)

    def merge(self, other: "UnknownTally") -> "UnknownTally":
        """Associatif et commutatif."""
        return UnknownTally(
            count=self.count + other.count,
            example=min(self.example, other.example, key=UnknownExample.sort_key),
        )
