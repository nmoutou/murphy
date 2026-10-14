"""Les mesures d'un run, fusionnables : chaque worker tient les siennes, le pipeline les
réduit. Le pendant de ``RunStats`` pour ``statistics`` : des tailles et des durées, pas
une comptabilité.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .distribution import Distribution

__all__ = ["MeasurePath", "RunMeasures"]

MeasurePath = tuple[str, ...]
"""Le chemin de la mesure dans le document ``statistics`` :
``("documents", "legi", "step_ms", "embed")``."""


@dataclass(frozen=True)
class RunMeasures:
    """Monoïde : neutre ``empty()``, ``merge`` associatif et commutatif."""

    distributions: Mapping[MeasurePath, Distribution] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> RunMeasures:
        return cls()

    def merge(self, other: RunMeasures) -> RunMeasures:
        merged = dict(self.distributions)
        for path, distribution in other.distributions.items():
            known = merged.get(path)
            merged[path] = distribution if known is None else known.merge(distribution)
        return RunMeasures(merged)

    @classmethod
    def reduce(cls, measures: Iterable[RunMeasures]) -> RunMeasures:
        result = cls.empty()
        for measure in measures:
            result = result.merge(measure)
        return result

    def to_document(self) -> dict[str, Any]:
        """Les chemins dépliés en sous-documents."""
        document: dict[str, Any] = {}
        for path, distribution in sorted(self.distributions.items()):
            *parents, leaf = path
            node = document
            for key in parents:
                node = node.setdefault(key, {})
            node[leaf] = distribution.to_document()
        return document
