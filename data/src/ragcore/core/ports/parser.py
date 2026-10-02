from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.collision import Collision
from ..models.document import ParsedDocument, RawDocument


@dataclass(frozen=True)
class ParseResult:
    """Ce que le parsing a produit, et ce qu'il a rangé sans qu'on le lui apprenne.

    Le parser est pur : ce qu'il constate voyage ici, et le site de parse le signale à
    la télémétrie. Les signaux sont tenus par clé chemin-complet, avec le fichier de la
    première facette qui la porte (ADR-024), et émis même quand ``skip_unconfigured``
    retire la donnée.

    - ``unconfigured_tags`` : clés de ``document.metadata`` non configurées (ADR-023),
      signal ``tags`` du bilan, que le curseur retire avant l'ingestion ;
    - ``unconfigured_links`` : liens heuristiques, signal ``links`` ;
    - ``unknown_roots`` : racines de facette hors table, signal seul ;
    - ``collisions`` : clés résolues en liste (ADR-025). Une collision non configurée
      refuse le document (``CollisionError``).
    """

    document: ParsedDocument
    unconfigured_tags: Mapping[str, str] = field(default_factory=dict)
    unconfigured_links: Mapping[str, str] = field(default_factory=dict)
    unknown_roots: Mapping[str, str] = field(default_factory=dict)
    collisions: tuple[Collision, ...] = ()


@runtime_checkable
class BaseParser(Protocol):
    """Lève ValidationError si le document est lisible mais irrecevable, ParseError s'il
    est illisible : les appelants qualifient le rejet par cette distinction.
    """

    def parse(self, raw: RawDocument) -> ParseResult: ...
