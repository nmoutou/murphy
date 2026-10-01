"""CollisionTally — ce que le bilan sait d'une clé en collision : combien, et où la voir.

Une collision se compte en DOCUMENTS : un document dont la clé reçoit plusieurs valeurs
compte une fois (ADR-049). L'exemple donne les fichiers d'où viennent ces valeurs : deux
facettes d'un texte LEGI se contredisent d'un fichier à l'autre, un seul fichier suffit
quand la balise se répète dans une facette.

La fusion doit rester commutative (cf. ``RunStats``) : l'exemple gardé est le PLUS PETIT
des deux, jamais « le premier vu », qui dépendrait de l'ordre de fin des workers.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["CollisionTally"]


class CollisionTally(BaseModel):
    """Le nombre de documents où une clé entre en collision, et les fichiers de l'un
    d'eux."""

    model_config = ConfigDict(frozen=True)

    count: int
    example: tuple[str, ...]
    """Les fichiers du document, distincts, dans l'ordre des valeurs : celui des facettes
    déclaré par la table."""

    @classmethod
    def seen_in(cls, source_files: tuple[str, ...]) -> "CollisionTally":
        """Une collision vue dans un document."""
        return cls(count=1, example=source_files)

    def merge(self, other: "CollisionTally") -> "CollisionTally":
        """Somme des comptes, plus petit exemple : associatif et commutatif."""
        return CollisionTally(
            count=self.count + other.count, example=min(self.example, other.example)
        )
