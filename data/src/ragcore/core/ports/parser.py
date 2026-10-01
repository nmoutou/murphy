from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.collision import Collision
from ..models.document import ParsedDocument, RawDocument


@dataclass(frozen=True)
class ParseResult:
    """Ce que le parsing a produit — et ce qu'il a rangé sans qu'on le lui apprenne.

    Le pendant, côté parse, d'``ExtractionResult`` : le parser est PUR (il ne connaît ni
    la télémétrie, ni l'environnement), donc ce qu'il constate voyage dans sa valeur de
    retour, et c'est l'appelant — le site de parse, qui tient la télémétrie — qui signale.

    Les signaux sont tenus par clé chemin-complet, chacune avec le fichier de la
    première facette qui la porte (ADR-048). Ils sont émis même quand le curseur
    ``skip_unconfigured`` retire la donnée : on compte d'abord, on filtre ensuite.

    - ``unconfigured_tags`` : les clés de ``document.metadata`` non-configurées — d'une
      balise absente de la table de rôles, ou connue sans renommage (ADR-047). C'est le
      signal ``tags`` du bilan, et la POIGNÉE du curseur : les retirer juste avant
      l'ingestion, sans retoucher le parser.
    - ``unconfigured_links`` : les clés des balises absentes de la table dont la valeur
      a la forme d'un identifiant DILA (liens heuristiques). Signal ``links`` du bilan ;
      le curseur retire leurs arêtes à l'extraction.
    - ``unknown_roots`` : les racines de facette hors table — une famille de documents
      jamais déclarée — avec leur fichier. Signal seul : une racine inconnue n'a pas de
      valeur à ingérer.
    - ``collisions`` : les clés qui ont reçu plusieurs valeurs distinctes (ADR-049),
      résolues en liste. Une collision NON configurée ne revient pas ici : elle refuse
      le document (``CollisionError``).
    """

    document: ParsedDocument
    unconfigured_tags: Mapping[str, str] = field(default_factory=dict)
    unconfigured_links: Mapping[str, str] = field(default_factory=dict)
    unknown_roots: Mapping[str, str] = field(default_factory=dict)
    collisions: tuple[Collision, ...] = ()


@runtime_checkable
class BaseParser(Protocol):
    """Interprétation d'un document brut.

    Lève ValidationError si le document est lisible mais irrecevable,
    ParseError s'il est illisible. Les appelants comptent sur cette
    distinction pour qualifier le rejet.
    """

    def parse(self, raw: RawDocument) -> ParseResult: ...
