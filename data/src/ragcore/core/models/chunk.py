from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .document import SCHEMA_VERSION
from .identifiers import Identifier, OwnerId


class Chunk(BaseModel):
    """Fragment d'un document parsé, prêt pour embedding."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = SCHEMA_VERSION
    chunk_id: str
    parent_identifier: Identifier  # lien au document parent
    owner_id: OwnerId

    ordinal: int
    text: str
    tag_path: list[str]
    char_start: int
    char_end: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddedChunk(BaseModel):
    """Chunk augmenté d'un vecteur d'embedding."""

    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    embedding: list[float]
    embedding_model: str
    embedding_dim: int
