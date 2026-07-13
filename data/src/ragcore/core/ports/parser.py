from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument, RawDocument


@runtime_checkable
class BaseParser(Protocol):
    """Interprétation d'un document brut.

    Lève ValidationError si le document est lisible mais irrecevable,
    ParseError s'il est illisible. Les appelants comptent sur cette
    distinction pour qualifier le rejet.
    """

    def parse(self, raw: RawDocument) -> ParsedDocument: ...
