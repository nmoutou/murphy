from dataclasses import dataclass

__all__ = ["FULL_RATIO", "SourceInventory"]

FULL_RATIO = 1.0
"""``ingestion_ratio`` d'un run complet."""


@dataclass(frozen=True)
class SourceInventory:
    """Ce que la passe 1 d'un connecteur a trouvé, sans rien lire (ADR-034 §1)."""

    total: int
    """Les clés de la source : un document par clé, quel que soit son nombre de
    facettes."""
    retained: int
    """Celles que ``ingestion_ratio`` garde, et que la passe 2 émettra."""
