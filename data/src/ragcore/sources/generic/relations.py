"""L'extracteur générique : l'adaptateur entre le port ``BaseRelationExtractor`` et
``core/links.extract_links``, pour que le worker n'ait pas à connaître la table de la
source qu'il traite.
"""

from __future__ import annotations

from ragcore.core.links import LinkSubject, extract_links
from ragcore.core.models import ParsedDocument, SourceName
from ragcore.core.ports.relation_extractor import ExtractionResult

from .role_table import RoleTable

__all__ = ["GenericRelationExtractor"]


class GenericRelationExtractor:
    """``skip_unconfigured`` retire les arêtes de type non configuré (ADR-048) ; le
    signal sort quand même.
    """

    def __init__(
        self, table: RoleTable, source: SourceName, *, skip_unconfigured: bool = False
    ) -> None:
        self._table = table
        self._source = source
        self._skip_unconfigured = skip_unconfigured

    @property
    def source_name(self) -> SourceName:
        return self._source

    def extract(self, document: ParsedDocument) -> ExtractionResult:
        links = self._table.links
        if links is None:
            # Une source sans table de liens n'a simplement pas d'arêtes
            return ExtractionResult()

        extracted = extract_links(
            references=document.structure.get("references", []),
            ancestors=document.structure.get("context", []),
            table=links,
            subject=LinkSubject(
                current=document.identifier,
                source=self._source,
            ),
        )
        unconfigured = (
            [] if self._skip_unconfigured else extracted.unconfigured_relations
        )
        return ExtractionResult(
            relations=extracted.relations + unconfigured,
            unformatted_relations=extracted.unformatted_relations,
            unknowns=extracted.unknowns,
            lost_links=extracted.lost_links,
        )
