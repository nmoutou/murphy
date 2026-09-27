"""L'extracteur générique — **le dernier module spécifique à disparaître**.

``LegiRelationExtractor`` était déjà une coquille de 45 lignes : il branchait la
``LinkTable`` de LEGI sur ``core/links`` et rendait la main. Une coquille par source, ça
reste une classe par source — et c'est exactement ce que §3 refuse.

Ce module est la même coquille, **paramétrée**. Il ne connaît ni LEGI, ni la
jurisprudence : il connaît une ``RoleTable``, qui porte la ``LinkTable``. Six sources, un
extracteur.

**Pourquoi il existe encore, alors qu'il ne fait presque rien.** Le port
``BaseRelationExtractor`` (``extract(document) -> ExtractionResult``) est ce que le worker
appelle. ``core/links.extract_links`` a une signature plus riche (elle prend la table et
le sujet : document, propriétaire, source). Ce module est l'adaptateur entre les deux — et
c'est un rôle réel : il évite que le worker ait à connaître la table de la source qu'il
traite.
"""

from __future__ import annotations

from ragcore.core.links import LinkSubject, extract_links
from ragcore.core.models import ParsedDocument, SourceName
from ragcore.core.ports.relation_extractor import ExtractionResult

from .role_table import RoleTable

__all__ = ["GenericRelationExtractor"]


class GenericRelationExtractor:
    """Branche la table d'une source sur la mécanique du domaine. Rien de plus."""

    def __init__(self, table: RoleTable, source: SourceName) -> None:
        self._table = table
        self._source = source

    @property
    def source_name(self) -> SourceName:
        return self._source

    def extract(self, document: ParsedDocument) -> ExtractionResult:
        links = self._table.links
        if links is None:
            # Une source sans table de liens n'a pas d'arêtes. Ce n'est pas une erreur —
            # c'est une source de documents purs. Rendre un résultat vide est la vérité ;
            # lever ici obligerait chaque source à déclarer une table qu'elle n'utilise pas.
            return ExtractionResult()

        extracted = extract_links(
            references=document.structure.get("references", []),
            ancestors=document.structure.get("context", []),
            table=links,
            subject=LinkSubject(
                current=document.identifier,
                owner_id=document.owner_id,
                source=self._source,
            ),
        )
        return ExtractionResult(
            relations=extracted.relations,
            unknowns=extracted.unknowns,
            citations=extracted.citations,
        )
