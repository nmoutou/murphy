"""RunStats — l'agrégat d'un run, MERGEABLE (monoïde de fusion, §11).

Avec N workers il n'y a plus *un* agrégateur mais N. Le verrou disparaît parce
que rien n'est partagé : chaque worker tient SON agrégat local, immuable, et le
pipeline les RÉDUIT. La fusion est une fonction pure — zéro section critique.
"""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from .unknown_tally import UnknownExample, UnknownTally

__all__ = ["RunStats"]


class RunStats(BaseModel):
    """Agrégat immuable et fusionnable des événements d'un run (ou d'un worker).

    Monoïde :
      - élément neutre : ``RunStats.empty()``
      - opérateur      : ``merge`` — associatif ET commutatif
      - lois           : ``merge(x, empty()) == merge(empty(), x) == x``
                         ``merge(merge(a, b), c) == merge(a, merge(b, c))``
                         ``merge(a, b) == merge(b, a)``

    La commutativité n'est pas un luxe, c'est une contrainte de correction : les
    workers finissent dans un ordre non déterministe. Une fusion non commutative
    ferait dépendre le RunSummary de l'ordonnancement — un non-déterminisme
    silencieux. Elle interdit donc tout champ du genre « le premier échec ».
    """

    model_config = ConfigDict(frozen=True)

    counts: dict[str, int] = Field(default_factory=dict)
    """event_type -> nombre d'occurrences. Fusion : somme."""

    unknowns: dict[str, dict[str, UnknownTally]] = Field(default_factory=dict)
    """Catégorie -> mot que le run n'a pas su nommer -> combien de documents, et un exemple.

    Un COMPTEUR par mot, en documents : chaque document ne déclare un mot qu'une fois.
    Fusion : somme des comptes, plus petit exemple (``UnknownTally.merge``).
    """

    @classmethod
    def empty(cls) -> "RunStats":
        """L'élément neutre du monoïde."""
        return cls()

    def merge(self, other: "RunStats") -> "RunStats":
        """Opérateur associatif et commutatif. Ne mute rien ; retourne un neuf."""
        counts = dict(self.counts)
        for event_type, n in other.counts.items():
            counts[event_type] = counts.get(event_type, 0) + n

        unknowns = {
            category: dict(tallies) for category, tallies in self.unknowns.items()
        }
        for category, tallies in other.unknowns.items():
            merged = unknowns.setdefault(category, {})
            for value, tally in tallies.items():
                known = merged.get(value)
                merged[value] = tally if known is None else known.merge(tally)

        return RunStats(counts=counts, unknowns=unknowns)

    @classmethod
    def reduce(cls, stats: Iterable["RunStats"]) -> "RunStats":
        """Réduit N agrégats en un seul. ``reduce([])`` vaut ``empty()``."""
        result = cls.empty()
        for stat in stats:
            result = result.merge(stat)
        return result

    def with_count(self, event_type: str, n: int = 1) -> "RunStats":
        return self.merge(RunStats(counts={event_type: n}))

    def with_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> "RunStats":
        """Un mot inconnu, vu dans un document de plus."""
        tally = UnknownTally.seen_in(example)
        return self.merge(RunStats(unknowns={category: {value: tally}}))
