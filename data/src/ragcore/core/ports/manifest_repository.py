from typing import Protocol, runtime_checkable

from ..models.identifiers import Identifier
from ..models.manifest import ManifestEntry


@runtime_checkable
class ManifestRepository(Protocol):
    """Registre d'idempotence — append-only avec deux modes d'indexation.

    Mode 1 (valides) : clé ``identifier`` — pour l'idempotence
    Mode 2 (rejetés) : clé ``source_path`` — pour l'audit
    """

    async def append(self, entry: ManifestEntry) -> None:
        """Ajoute une nouvelle entrée (append-only)."""
        ...

    async def last_for_identifier(self, identifier: Identifier) -> ManifestEntry | None:
        """Récupère la dernière entrée pour cet identifier (tri par processed_at DESC)."""
        ...

    async def delete(self, identifier: Identifier) -> None:
        """Supprime toutes les entrées pour cet identifier."""
        ...
