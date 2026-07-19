"""Le port ``Scorer`` — couture pour B-13 (l'orchestrateur de sweep).

B-13 pilotera un balayage `(W, R)` (ADR-027) et devra scorer de nombreux
couples `(qrels, run)`. Il dépendra de ce ``Protocol``, jamais de la fonction
concrète ``core.services.report.score`` — même discipline que les ports
``ragcore`` (``core/ports/embedder.py`` etc.) : le domaine dépend d'une
interface, l'implémentation est substituable sans toucher l'appelant.
"""

from __future__ import annotations

from typing import Protocol

from murphy_eval.core.models.gains import GainFn, exponential_gain
from murphy_eval.core.models.judgment import Qrels
from murphy_eval.core.models.metrics import MetricsReport
from murphy_eval.core.models.run import Run


class Scorer(Protocol):
    def score(
        self,
        qrels: Qrels,
        run: Run,
        *,
        gain: GainFn = exponential_gain,
        action_types: dict[str, str] | None = None,
    ) -> MetricsReport: ...
