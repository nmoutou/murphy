from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument, RawDocument


@dataclass(frozen=True)
class ParseResult:
    """Ce que le parsing a produit — et ce qu'il a rangé sans qu'on le lui apprenne.

    Le pendant, côté parse, d'``ExtractionResult`` : le parser est PUR (il ne connaît ni
    la télémétrie, ni l'environnement), donc ce qu'il constate voyage dans sa valeur de
    retour, et c'est l'appelant — le site de parse, qui tient la télémétrie — qui signale.

    - ``unconfigured_tags`` : les balises non-configurées — absentes de la table de
      rôles, ou connues mais sans renommage dans ``meta_renames`` (ADR-047) — chacune
      avec le fichier de la première facette qui la porte. C'est le SIGNAL
      (``tag.unconfigured``) — la vigie de dérive DILA. Il est émis même quand la
      donnée est ingérée : on compte d'abord, on filtre ensuite.
    - ``unconfigured_keys`` : les clés de ``document.metadata`` que ces balises ont
      produites (clé chemin-complet). C'est la POIGNÉE du curseur ``skip`` : les
      retirer juste avant l'ingestion, sans retoucher le parser.
    - ``unknown_roots`` : les racines de facette hors table — une famille de documents
      jamais déclarée — avec leur fichier. Signal seul : une racine inconnue n'a pas de
      valeur à ingérer.
    """

    document: ParsedDocument
    unconfigured_tags: Mapping[str, str] = field(default_factory=dict)
    unconfigured_keys: tuple[str, ...] = field(default=())
    unknown_roots: Mapping[str, str] = field(default_factory=dict)


@runtime_checkable
class BaseParser(Protocol):
    """Interprétation d'un document brut.

    Lève ValidationError si le document est lisible mais irrecevable,
    ParseError s'il est illisible. Les appelants comptent sur cette
    distinction pour qualifier le rejet.
    """

    def parse(self, raw: RawDocument) -> ParseResult: ...
