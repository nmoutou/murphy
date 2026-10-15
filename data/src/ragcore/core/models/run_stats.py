"""L'agrégat d'un run, fusionnable : chaque worker tient le sien, immuable, et le
pipeline les réduit. Rien n'est partagé, donc aucun verrou.
"""

from collections.abc import Iterable, Mapping
from typing import Protocol, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field

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


def _sum_counts(left: Mapping[str, int], right: Mapping[str, int]) -> dict[str, int]:
    summed = dict(left)
    for key, n in right.items():
        summed[key] = summed.get(key, 0) + n
    return summed


class RunStats(BaseModel):
    """Monoïde : neutre ``empty()``, opérateur ``merge`` associatif et commutatif.

    La commutativité est requise : les workers finissent dans un ordre non déterministe.
    Elle interdit tout champ du genre « le premier échec ».
    """

    model_config = ConfigDict(frozen=True)

    counts: dict[str, int] = Field(default_factory=dict)
    """event_type, ou compteur par raison (``telemetry_events``) -> nombre
    d'occurrences."""

    unknowns: dict[str, dict[str, UnknownTally]] = Field(default_factory=dict)
    """Catégorie -> mot que le run n'a pas su nommer -> nombre de documents et exemple."""

    @classmethod
    def empty(cls) -> "RunStats":
        return cls()

    def merge(self, other: "RunStats") -> "RunStats":
        unknowns = {
            category: _merge_tallies(
                self.unknowns.get(category, {}), other.unknowns.get(category, {})
            )
            for category in dict.fromkeys([*self.unknowns, *other.unknowns])
        }
        return RunStats(
            counts=_sum_counts(self.counts, other.counts),
            unknowns=unknowns,
        )

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
