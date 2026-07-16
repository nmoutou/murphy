"""Le multi-source — **composer, pas généraliser**.

Un run peut ingérer plusieurs sources. Ce module rend cela possible sans qu'aucune
brique existante n'ait à savoir qu'elle n'est plus seule : le connecteur, le parser et
l'extracteur de LEGI ignorent toujours qu'il existe cinq bases de jurisprudence.

**La composition passe par le port, pas par une exception au port.** ``CompositeConnector``
*est* un ``BaseConnector`` ; ``RoutingParser`` expose la même surface qu'un ``GenericParser``.
Les nœuds Kedro ne voient donc aucune différence entre un run mono-source et un run à six
sources — c'est ce qui permet de changer le défaut sans toucher au DAG.

**Ce qui rend le routage possible, et qui n'a rien coûté :** ``RawDocument`` porte
**déjà** sa source, estampillée par le connecteur qui l'a émis. Un flux mêlant six
sources n'est donc jamais ambigu — chaque document sait d'où il vient. Router, c'est
lire ce champ ; il n'y a ni heuristique, ni devinette, ni ordre à préserver.

**Pourquoi router plutôt que rendre le parser multi-tables.** Une ``RoleTable`` décrit
*une* source, et six sources n'ont pas la même (LEGI, JURI_JUDI, JURI_ADMIN et
JURI_CONSTIT en sont quatre distinctes). Faire tenir six tables au ``GenericParser``
aurait dilué son contrat pour un besoin qui n'est pas le sien. Le routage vit donc
**au-dessus**, dans des objets dont c'est le seul métier — le motif que
``sources/registry.py`` a déjà institué contre les ``if source == …``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Mapping

from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.relation_extractor import ExtractionResult
from ragcore.sources.generic.parser import GenericParser
from ragcore.sources.generic.relations import GenericRelationExtractor

__all__ = ["CompositeConnector", "RoutingParser", "RoutingRelationExtractor"]


def _unroutable(
    source: SourceName, known: Iterable[SourceName], role: str
) -> ValueError:
    """L'erreur d'un document qu'on ne sait pas router.

    Ce cas ne devrait pas exister : le composite ne produit que des documents des sources
    qu'on lui a données. S'il survient, c'est qu'un connecteur a estampillé un document
    d'une source qui n'est pas la sienne — et il faut le savoir *tout de suite*. Router au
    hasard (ou vers un défaut) parserait le document avec la **mauvaise table de rôles** :
    il en sortirait un document plausible et silencieusement faux, c'est-à-dire la seule
    famille de bug que ce pipeline s'interdit.
    """
    connues = ", ".join(sorted(s.value for s in known))
    return ValueError(
        f"Aucun {role} pour la source {source.value!r}. Sources de ce run : {connues}."
    )


class CompositeConnector:
    """``BaseConnector`` qui enchaîne les connecteurs de plusieurs sources.

    Séquentiel, et délibérément : le parallélisme du pipeline est **inter-document** (le
    pool de workers de la phase 1), pas inter-source. Paralléliser ici ne gagnerait rien
    — la lecture disque n'est pas le goulot — et ferait entrer une seconde forme de
    concurrence dans un module qui n'a aucune raison d'en connaître une.
    """

    def __init__(self, connectors: Mapping[SourceName, BaseConnector]) -> None:
        if not connectors:
            msg = (
                "CompositeConnector sans aucune source : un run qui ne lit rien "
                "se terminerait « ok » en n'ingérant rien."
            )
            raise ValueError(msg)
        self._connectors = dict(connectors)
        self.skipped: dict[str, int] = {}
        """Ce que les connecteurs ont écarté, **fusionné**.

        Un fichier illisible dans CASS et un autre dans JADE font deux exclusions, pas
        une. Le port expose ce compteur précisément pour qu'un document écarté soit
        *compté* plutôt que de disparaître ; le composite ne peut pas être l'endroit où
        cette garantie se perd.
        """

    @property
    def sources(self) -> tuple[SourceName, ...]:
        """Les sources composées, dans l'ordre d'itération."""
        return tuple(self._connectors)

    async def fetch_all(self, owner_id: OwnerId) -> AsyncIterator[RawDocument]:
        """Itère les documents de toutes les sources, source par source.

        Générateur de bout en bout : le corpus complet n'est jamais en mémoire, pas plus
        à six sources qu'à une.
        """
        self.skipped = {}

        for connector in self._connectors.values():
            async for document in connector.fetch_all(owner_id):
                yield document

            # Après épuisement, jamais avant : `skipped` se remplit au fil de la lecture.
            # Le lire trop tôt rendrait zéro — et un compteur d'exclusions vide est
            # indiscernable d'une absence d'exclusion.
            for reason, count in getattr(connector, "skipped", {}).items():
                self.skipped[reason] = self.skipped.get(reason, 0) + count


class RoutingParser:
    """Le parser du run : délègue au ``GenericParser`` de la source de chaque document."""

    def __init__(self, parsers: Mapping[SourceName, GenericParser]) -> None:
        if not parsers:
            msg = "RoutingParser sans parser : aucun document ne pourrait être interprété."
            raise ValueError(msg)
        self._parsers = dict(parsers)

    def parse(self, raw: RawDocument) -> ParsedDocument:
        parser = self._parsers.get(raw.source)
        if parser is None:
            raise _unroutable(raw.source, self._parsers, "parser")
        return parser.parse(raw)


class RoutingRelationExtractor:
    """L'extracteur du run : délègue à l'extracteur de la source du document."""

    def __init__(
        self, extractors: Mapping[SourceName, GenericRelationExtractor]
    ) -> None:
        if not extractors:
            msg = (
                "RoutingRelationExtractor sans extracteur : les relations de tous les "
                "documents seraient perdues en silence."
            )
            raise ValueError(msg)
        self._extractors = dict(extractors)

    def extract(self, document: ParsedDocument) -> ExtractionResult:
        extractor = self._extractors.get(document.source)
        if extractor is None:
            raise _unroutable(
                document.source, self._extractors, "extracteur de relations"
            )
        return extractor.extract(document)
