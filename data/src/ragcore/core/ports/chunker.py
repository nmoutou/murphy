from typing import Protocol, runtime_checkable

from ..models.chunk import Chunk
from ..models.document import ParsedDocument


@runtime_checkable
class BaseChunker(Protocol):
    """Découpage d'un document en fragments indexables."""

    def chunk(self, document: ParsedDocument) -> list[Chunk]: ...
