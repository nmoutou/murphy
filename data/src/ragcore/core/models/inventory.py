from dataclasses import dataclass

__all__ = ["SourceInventory"]


@dataclass(frozen=True)
class SourceInventory:
    """Ce que la passe 1 d'un connecteur a trouvé, sans rien lire (ADR-034 §1)."""

    documents: int
    """Les clés à émettre : un document par clé, quel que soit son nombre de
    facettes."""
