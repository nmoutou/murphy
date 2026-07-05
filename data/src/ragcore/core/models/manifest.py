from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .document import SCHEMA_VERSION
from .enums import Operation, SourceName
from .identifiers import OwnerId, SourceIdentifier


class ManifestEntry(BaseModel):
    """Entrée du registre de traitement — append-only.
    
    Trackage de toutes les tentatives de traitement :
    - Valides : `identifier` rempli, `source_path` optionnel (debug)
    - Rejetés : `identifier=None`, `source_path` obligatoire, `reason` obligatoire
    
    Deux modes d'indexation coexistent :
    1. Pour idempotence (valides) : clé (identifier, owner_id)
    2. Pour audit des rejets : clé (source_path, owner_id)
    """

    model_config = ConfigDict(frozen=True)

    # Identifiants
    entry_id: UUID = Field(default_factory=uuid4)
    schema_version: int = SCHEMA_VERSION

    # Clés d'indexation (mutuellement exclusives selon operation)
    identifier: SourceIdentifier | None = None  # Non-null pour valides
    source_path: str | None = None              # Pour rejets et debug

    # Contexte
    owner_id: OwnerId
    source: SourceName
    operation: Operation

    # Raison d'exclusion (obligatoire pour EXCLUDED)
    reason: str | None = None

    # Résultat
    targets_written: list[str] = Field(default_factory=list)
    processed_at: datetime

    @model_validator(mode="after")
    def _validate_excluded_coherence(self) -> "ManifestEntry":
        """Valide les invariants pour les opérations EXCLUDED."""
        if self.operation == Operation.EXCLUDED:
            if self.reason is None or not self.reason.strip():
                raise ValueError("EXCLUDED entries must have a non-empty `reason`")
            if self.identifier is not None:
                raise ValueError("EXCLUDED entries must have `identifier=None`")
            if self.source_path is None or not self.source_path.strip():
                raise ValueError("EXCLUDED entries must have a non-empty `source_path`")
        return self
