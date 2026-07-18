from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument, RawDocument


@dataclass(frozen=True)
class ParseResult:
    """Ce que le parsing a produit — et ce qu'il a rangé sans qu'on le lui apprenne.

    Le pendant, côté parse, d'``ExtractionResult`` : le parser est PUR (il ne connaît ni
    la télémétrie, ni l'environnement), donc ce qu'il constate voyage dans sa valeur de
    retour, et c'est l'appelant — le site de parse, qui tient la télémétrie — qui signale.

    - ``unconfigured_tags`` : les balises que la table de rôles ne connaît pas, dédupli-
      quées. C'est le SIGNAL (``tag.unconfigured``) — la vigie de dérive DILA. Il est
      émis même quand la donnée est ingérée : on compte d'abord, on filtre ensuite.
    - ``unconfigured_keys`` : les clés de ``document.metadata`` que ces balises ont
      produites (cascade « trois portes », porte metadata). C'est la POIGNÉE du curseur
      ``skip`` : les retirer juste avant l'ingestion, sans retoucher le parser.
    - ``unknown_roots`` : les racines de facette hors table — une famille de documents
      jamais déclarée. Signal seul : une racine inconnue n'a pas de valeur à ingérer.
    """

    document: ParsedDocument
    unconfigured_tags: tuple[str, ...] = field(default=())
    unconfigured_keys: tuple[str, ...] = field(default=())
    unknown_roots: tuple[str, ...] = field(default=())


@runtime_checkable
class BaseParser(Protocol):
    """Interprétation d'un document brut.

    Lève ValidationError si le document est lisible mais irrecevable,
    ParseError s'il est illisible. Les appelants comptent sur cette
    distinction pour qualifier le rejet.
    """

    def parse(self, raw: RawDocument) -> ParseResult: ...
