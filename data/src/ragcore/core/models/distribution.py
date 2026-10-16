"""Une mesure en distribution : une moyenne seule ne dit rien d'une longue traîne.

Fusionnable dans n'importe quel ordre, comme ``RunStats`` : chaque worker tient les
siennes, réunies en fin de run sans verrou.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["Distribution"]


@dataclass(frozen=True, slots=True)
class Distribution:
    """Une dataclass et non un modèle pydantic : une par mesure et par document, des
    millions par run."""

    count: int
    sum: float
    min: float
    max: float
    max_ref: str
    """Ce qui a donné le maximum : un identifiant de document, de composante."""

    @classmethod
    def of(cls, value: float, ref: str) -> Distribution:
        return cls(
            count=1,
            sum=value,
            min=value,
            max=value,
            max_ref=ref,
        )

    @property
    def mean(self) -> float:
        return self.sum / self.count

    def merge(self, other: Distribution) -> Distribution:
        return Distribution(
            count=self.count + other.count,
            sum=self.sum + other.sum,
            min=min(self.min, other.min),
            max=max(self.max, other.max),
            max_ref=self._max_ref_with(other),
        )

    def _max_ref_with(self, other: Distribution) -> str:
        """À maximum égal, la plus petite référence : « la première vue » dépendrait de
        l'ordre des workers."""
        if self.max != other.max:
            return self.max_ref if self.max > other.max else other.max_ref
        return min(self.max_ref, other.max_ref)

    def to_document(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "sum": self.sum,
            "min": self.min,
            "max": self.max,
            "mean": self.mean,
            "max_ref": self.max_ref,
        }
