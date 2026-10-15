"""Le multi-source, par composition : chaque routeur respecte le port de ce qu'il
compose, et les nœuds ne voient pas la différence avec un run mono-source.

Le routage lit la source que chaque ``RawDocument`` porte déjà : un flux mêlé n'est
jamais ambigu.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping

from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.models.problems import FileProblem
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.parser import ParseResult
from ragcore.core.ports.relation_extractor import ExtractionResult
from ragcore.sources.generic.parser import GenericParser
from ragcore.sources.generic.relations import GenericRelationExtractor

__all__ = ["CompositeConnector", "RoutingParser", "RoutingRelationExtractor"]


def _unroutable(
    source: SourceName, known: Iterable[SourceName], role: str
) -> ValueError:
    """Un connecteur a estampillé un document d'une autre source. Jamais de routage par
    défaut : la mauvaise table de rôles donnerait un document plausible et faux.
    """
    connues = ", ".join(sorted(s.value for s in known))
    return ValueError(
        f"Aucun {role} pour la source {source.value!r}. Sources de ce run : {connues}."
    )


class CompositeConnector:
    """Enchaîne les connecteurs, séquentiellement : la lecture disque n'est pas le
    goulot, et le parallélisme est celui du pool de la phase 1.
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
        """Ce que les connecteurs ont écarté, sommé par raison."""
        self.collisions: list[CollisionRecord] = []
        self.problems: list[FileProblem] = []

    @property
    def sources(self) -> tuple[SourceName, ...]:
        return tuple(self._connectors)

    def discover(self) -> dict[SourceName, SourceInventory]:
        """Toutes les sources avant la première lecture."""
        inventories: dict[SourceName, SourceInventory] = {}
        for connector in self._connectors.values():
            inventories.update(connector.discover())
        return inventories

    def fetch_all(self) -> Iterator[RawDocument]:
        """Générateur de bout en bout : le corpus n'est jamais entier en mémoire."""
        self.skipped = {}
        self.collisions = []
        self.problems = []

        for connector in self._connectors.values():
            yield from connector.fetch_all()

            # Après épuisement : `skipped`, `collisions` et `problems` se remplissent au
            # fil de la lecture
            for reason, count in connector.skipped.items():
                self.skipped[reason] = self.skipped.get(reason, 0) + count
            self.collisions.extend(connector.collisions)
            self.problems.extend(connector.problems)


class RoutingParser:
    """Délègue au ``GenericParser`` de la source de chaque document."""

    def __init__(self, parsers: Mapping[SourceName, GenericParser]) -> None:
        if not parsers:
            msg = "RoutingParser sans parser : aucun document ne pourrait être interprété."
            raise ValueError(msg)
        self._parsers = dict(parsers)

    def parse(self, raw: RawDocument) -> ParseResult:
        parser = self._parsers.get(raw.source)
        if parser is None:
            raise _unroutable(raw.source, self._parsers, "parser")
        return parser.parse(raw)


class RoutingRelationExtractor:
    """Délègue à l'extracteur de la source du document."""

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
