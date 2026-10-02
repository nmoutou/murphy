"""L'agrégat d'un run, fusionnable : chaque worker tient le sien, immuable, et le
pipeline les réduit. Rien n'est partagé, donc aucun verrou.
"""

from collections.abc import Iterable, Mapping
from typing import Protocol, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .collision_tally import CollisionTally
from .unknown_tally import UnknownExample, UnknownTally

__all__ = ["RunStats"]


class _Tally(Protocol):
    def merge(self, other: Self) -> Self: ...


_TallyT = TypeVar("_TallyT", bound=_Tally)


def _merge_tallies(
    left: Mapping[str, _TallyT], right: Mapping[str, _TallyT]
) -> dict[str, _TallyT]:
    merged = dict(left)
    for key, tally in right.items():
        known = merged.get(key)
        merged[key] = tally if known is None else known.merge(tally)
    return merged


class RunStats(BaseModel):
    """Monoïde : neutre ``empty()``, opérateur ``merge`` associatif et commutatif.

    La commutativité est requise : les workers finissent dans un ordre non déterministe.
    Elle interdit tout champ du genre « le premier échec ».
    """

    model_config = ConfigDict(frozen=True)

    counts: dict[str, int] = Field(default_factory=dict)
    """event_type -> nombre d'occurrences."""

    unknowns: dict[str, dict[str, UnknownTally]] = Field(default_factory=dict)
    """Catégorie -> mot que le run n'a pas su nommer -> nombre de documents et exemple."""

    collisions: dict[str, CollisionTally] = Field(default_factory=dict)
    """Clé de métadonnée qui a reçu plusieurs valeurs -> nombre de documents et
    fichiers de l'un d'eux (ADR-025)."""

    @classmethod
    def empty(cls) -> "RunStats":
        return cls()

    def merge(self, other: "RunStats") -> "RunStats":
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
        result = cls.empty()
        for stat in stats:
            result = result.merge(stat)
        return result

    def with_count(self, event_type: str, n: int = 1) -> "RunStats":
        return self.merge(RunStats(counts={event_type: n}))

    def with_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> "RunStats":
        tally = UnknownTally.seen_in(example)
        return self.merge(RunStats(unknowns={category: {value: tally}}))

    def with_collision(self, key: str, source_files: tuple[str, ...]) -> "RunStats":
        tally = CollisionTally.seen_in(source_files)
        return self.merge(RunStats(collisions={key: tally}))
