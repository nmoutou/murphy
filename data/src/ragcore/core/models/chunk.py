from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import DocumentType
from .identifiers import Identifier


class Chunk(BaseModel):
    """Fragment d'un document parsé, prêt pour embedding."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    parent_identifier: Identifier
    document_type: DocumentType  # celui du parent
    nature: str | None = None  # celle du parent

    ordinal: int
    text: str
    tag_path: list[str]
    char_start: int
    char_end: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddedChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    embedding: list[float]
    embedding_model: str
    embedding_dim: int
