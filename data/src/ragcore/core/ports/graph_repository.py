from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.enums import SourceName
from ..models.identifiers import OwnerId, SourceIdentifier
from ..models.relation import Relation


@runtime_checkable
class GraphRepository(Protocol):
    """Stockage du graphe (Neo4j) — merge intelligent (pas de delete-node)."""

    async def initialize(self) -> None:
        """Crée les index Neo4j pour chaque source configurée."""
        ...

    async def merge_document_node(self, document: ParsedDocument) -> None: ...

    async def upsert_relations(self, relations: list[Relation]) -> None: ...

    async def delete_relations_from(
        self, identifier: SourceIdentifier, owner_id: OwnerId, source: SourceName
    ) -> None:
        """Supprime uniquement les relations sortantes (préserve les entrantes)."""
        ...
