from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from .enums import SourceName
from .identifiers import OwnerId, SourceIdentifier

SCHEMA_VERSION = 1


class RawDocument(BaseModel):
    """Document tel que récupéré par le connector, avant parsing."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    source_document_id: str
    payload: dict[str, Any]
    fetched_at: datetime
    owner_id: OwnerId


class ParsedDocument(BaseModel):
    """Document après parsing : structuré, prêt pour chunking.
    
    Changements post-refonte :
    - `identifier: SourceIdentifier` remplace `document_id` et `eli` (union discriminée)
    - `content_hash` supprimé (idempotence simplifiée)
    """

    model_config = ConfigDict(frozen=True)

    schema_version: int = SCHEMA_VERSION
    identifier: SourceIdentifier
    source: SourceName
    owner_id: OwnerId

    title: str
    content: str
    structure: dict[str, Any]
    metadata: dict[str, Any]

    parsed_at: datetime
