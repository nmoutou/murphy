"""UnknownTally — ce que le bilan sait d'un mot inconnu : combien, et où le voir.

Un inconnu se compte en DOCUMENTS : un document qui porte trois fois la même balise
compte une fois. L'exemple est un document qui la porte, pour aller la lire.

La fusion doit rester commutative (cf. ``RunStats``) : l'exemple gardé est le PLUS PETIT
des deux, jamais « le premier vu », qui dépendrait de l'ordre de fin des workers.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["UnknownExample", "UnknownTally"]


class UnknownExample(BaseModel):
    """Un document qui porte l'inconnu, et le fichier où le lire."""

    model_config = ConfigDict(frozen=True)

    identifier: str
    source_file: str
    """Vide quand le document n'a pas de fichier source connu."""

    def sort_key(self) -> tuple[str, str]:
        return (self.identifier, self.source_file)


class UnknownTally(BaseModel):
    """Le nombre de documents qui portent un inconnu, et l'un d'eux."""

    model_config = ConfigDict(frozen=True)

    count: int
    example: UnknownExample

    @classmethod
    def seen_in(cls, example: UnknownExample) -> "UnknownTally":
        """Un inconnu vu dans un document."""
        return cls(count=1, example=example)

    def merge(self, other: "UnknownTally") -> "UnknownTally":
        """Somme des comptes, plus petit exemple : associatif et commutatif."""
        return UnknownTally(
            count=self.count + other.count,
            example=min(self.example, other.example, key=UnknownExample.sort_key),
        )
