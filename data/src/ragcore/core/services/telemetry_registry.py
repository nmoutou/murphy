"""Registre de télémétrie configuré par event_type.

Permet une granularité fine du routage des événements vers les backends.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EventBehavior:
    """Comportement d'un type d'événement : level + destination backends."""

    level: str  # "debug" | "info" | "warning" | "error"
    log: bool  # → ConsoleLogTelemetry (stdout)
    track_jsonl: bool  # → JsonlFileTelemetry (fichier local)
    track_mongo: bool  # → MongoAuditTelemetryAdapter (audit MongoDB)
    aggregate: bool  # → RunStatsAggregator (stats en mémoire + run_summary)


# Comportement par défaut pour les événements non listés explicitement
_DEFAULT_BEHAVIOR = EventBehavior(
    level="warning",
    log=True,
    track_jsonl=True,
    track_mongo=True,
    aggregate=True,
)


class TelemetryRegistry:
    """Mappe chaque event_type à son EventBehavior.

    Construit depuis un EVENT_CATALOG Python (méthode préférée)
    ou depuis parameters.yml pour des overrides ponctuels.
    """

    def __init__(
        self,
        behaviors: dict[str, EventBehavior],
        default: EventBehavior = _DEFAULT_BEHAVIOR,
    ):
        """
        Args:
            behaviors: Dict[event_type, EventBehavior] listés explicitement
            default: EventBehavior appliqué pour les event_type non listés
        """
        self._behaviors = behaviors
        self._default = default

    def behavior_for(self, event_type: str) -> EventBehavior:
        """Récupère le comportement pour cet event_type.

        Retourne le comportement spécifique s'il est dans la registry,
        sinon retourne le comportement par défaut.
        """
        return self._behaviors.get(event_type, self._default)

    @classmethod
    def from_params(cls, params: dict[str, Any]) -> "TelemetryRegistry":
        """Construit le registry depuis la config parameters.yml.

        Args:
            params: Config dict {
                "default": {...EventBehavior fields...},
                "events": {
                    "event.type.1": {...EventBehavior fields...},
                    ...
                }
            }
        """

        def _build(cfg: dict[str, Any], base: EventBehavior) -> EventBehavior:
            """Construis un EventBehavior depuis une config partielle, hérittant du base."""
            return EventBehavior(
                level=cfg.get("level", base.level),
                log=cfg.get("log", base.log),
                track_jsonl=cfg.get("track_jsonl", base.track_jsonl),
                track_mongo=cfg.get("track_mongo", base.track_mongo),
                aggregate=cfg.get("aggregate", base.aggregate),
            )

        # Comportement par défaut (peut override _DEFAULT_BEHAVIOR)
        default = _build(params.get("default", {}), _DEFAULT_BEHAVIOR)

        # Comportements spécifiques par event_type
        behaviors = {
            event_type: _build(cfg, default)
            for event_type, cfg in params.get("events", {}).items()
        }

        return cls(behaviors=behaviors, default=default)

    @classmethod
    def from_catalog(
        cls,
        catalog: dict[str, EventBehavior],
        default: EventBehavior = _DEFAULT_BEHAVIOR,
    ) -> "TelemetryRegistry":
        """Construit le registry depuis un catalogue Python (source de vérité).

        Args:
            catalog: Dict[event_type, EventBehavior] — typiquement EVENT_CATALOG
                     importé depuis ragcore.core.telemetry_events
            default: EventBehavior pour les event_type absents du catalogue
        """
        return cls(behaviors=dict(catalog), default=default)
