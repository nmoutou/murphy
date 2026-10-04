from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.identifiers import Identifier
from ..models.search_content import SearchContent


@runtime_checkable
class SearchIndexRepository(Protocol):
    """L'index de recherche (OpenSearch) : un document entier, passages compris."""

    async def index_document(
        self, parsed: ParsedDocument, content: SearchContent
    ) -> None:
        """Remplace le document s'il existe déjà."""
        ...

    async def delete_document(self, identifier: Identifier) -> None:
        """Sans erreur si le document n'existe pas."""
        ...
