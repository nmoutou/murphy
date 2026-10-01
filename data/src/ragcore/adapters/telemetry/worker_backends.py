"""Les backends d'un worker, chacun dans un champ nommé.

Brancher un nouvel outil, c'est ajouter un champ ici et le livrer dans
``WorkerTelemetryStack.emit``.
"""

from dataclasses import dataclass

from ragcore.core.ports.telemetry import TelemetryPort

from .aggregator import RunStatsAggregator

__all__ = ["WorkerBackends"]


@dataclass(frozen=True)
class WorkerBackends:
    """``aggregate`` est un ``RunStatsAggregator`` concret : il porte le bilan, pas
    seulement les événements."""

    log: TelemetryPort
    aggregate: RunStatsAggregator

    def closable_in_order(self) -> list[tuple[str, TelemetryPort]]:
        """``aggregate`` en dernier : il rend le bilan. Le nom sert aux logs d'échec."""
        return [
            ("log", self.log),
            ("aggregate", self.aggregate),
        ]
