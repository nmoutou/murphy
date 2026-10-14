"""Les mesures d'un run, telles que ``MURPHY_META.statistics`` les garde (ADR-034 §8).

La frontière avec ``RunSummary`` : le bilan compte ce qui est arrivé aux objets, et le
statut s'en dérive ; ``RunStatistics`` mesure des tailles et des durées, jamais lues
pour décider.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .identifiers import RunId
from .run_measures import RunMeasures

__all__ = ["RunStatistics"]


@dataclass(frozen=True)
class RunStatistics:
    run_id: RunId
    started_at: datetime
    stages_s: Mapping[str, float]
    """La durée de chaque étape du run, en secondes."""
    measures: RunMeasures

    def to_document(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "stages_s": dict(self.stages_s),
            **self.measures.to_document(),
        }
