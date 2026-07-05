from typing import Protocol, runtime_checkable

from ..models.identifiers import OwnerId, SourceIdentifier
from ..models.manifest import ManifestEntry


@runtime_checkable
class ManifestRepository(Protocol):
    """Registre d'idempotence — append-only avec deux modes d'indexation.
    
    Mode 1 (valides) : clé (identifier, owner_id) — pour l'idempotence
    Mode 2 (rejetés) : clé (source_path, owner_id) — pour l'audit
    """

    async def append(self, entry: ManifestEntry) -> None:
        """Ajoute une nouvelle entrée (append-only)."""
        ...

    async def last_for_identifier(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> ManifestEntry | None:
        """Récupère la dernière entrée pour cet identifier (tri par processed_at DESC)."""
        ...

    async def last_for_source_path(
        self, source_path: str, owner_id: OwnerId
    ) -> ManifestEntry | None:
        """Récupère la dernière entrée pour ce chemin source (pour audit des rejets)."""
        ...

    async def delete(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None:
        """Supprime toutes les entrées pour cet identifier."""
        ...
