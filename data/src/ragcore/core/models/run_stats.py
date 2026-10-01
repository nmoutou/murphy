"""RunStats — l'agrégat d'un run, MERGEABLE (monoïde de fusion, §11).

Avec N workers il n'y a plus *un* agrégateur mais N. Le verrou disparaît parce
que rien n'est partagé : chaque worker tient SON agrégat local, immuable, et le
pipeline les RÉDUIT. La fusion est une fonction pure — zéro section critique.
"""

from collections.abc import Iterable, Mapping
from typing import Protocol, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .collision_tally import CollisionExample, CollisionTally
from .unknown_tally import UnknownExample, UnknownTally

__all__ = ["RunStats"]


class _Tally(Protocol):
    def merge(self, other: Self) -> Self: ...


_TallyT = TypeVar("_TallyT", bound=_Tally)


def _merge_tallies(
    left: Mapping[str, _TallyT], right: Mapping[str, _TallyT]
) -> dict[str, _TallyT]:
    """Une clé vue des deux côtés fusionne ses comptes ; les autres passent telles quelles."""
    merged = dict(left)
    for key, tally in right.items():
        known = merged.get(key)
        merged[key] = tally if known is None else known.merge(tally)
    return merged


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

    collisions: dict[str, CollisionTally] = Field(default_factory=dict)
    """Clé de métadonnée qui a reçu plusieurs valeurs -> combien de documents, et les
    fichiers de l'un d'eux (ADR-049). Ce n'est pas un inconnu : la table range la clé en
    liste, ou refuse le document. Fusion : celle des inconnus (``CollisionTally.merge``).
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
            category: _merge_tallies(
                self.unknowns.get(category, {}), other.unknowns.get(category, {})
            )
            for category in dict.fromkeys([*self.unknowns, *other.unknowns])
        }
        collisions = _merge_tallies(self.collisions, other.collisions)

        return RunStats(counts=counts, unknowns=unknowns, collisions=collisions)

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

    def with_collision(self, key: str, example: CollisionExample) -> "RunStats":
        """Une clé en collision, vue dans un document de plus."""
        tally = CollisionTally.seen_in(example)
        return self.merge(RunStats(collisions={key: tally}))
