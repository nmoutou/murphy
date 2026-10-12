"""Le corps d'un document OpenSearch, construit depuis le document parsé."""

from typing import Any

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.search_content import IndexedPassage, SearchContent
from ragcore.core.services.parent_text_titles import parent_text_titles

__all__ = ["build_index_document"]


def build_index_document(
    parsed: ParsedDocument, content: SearchContent
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "identifier": parsed.identifier.serialize(),
        "document_type": parsed.document_type.value,
        "nature": parsed.nature,
        "title": parsed.title,
        "metadata": parsed.metadata,
        "passages": [_passage(passage) for passage in content.passages],
    }
    parent_titles = parent_text_titles(parsed)
    if parent_titles:
        body["parent_text_title"] = parent_titles
    if content.title_embedding is not None:
        body["title_embedding"] = content.title_embedding
    return body


def _passage(passage: IndexedPassage) -> dict[str, Any]:
    chunk = passage.chunk
    body: dict[str, Any] = {
        "chunk_id": chunk.chunk_id,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "text": chunk.text,
    }
    if passage.embedding is not None:
        body["embedding"] = passage.embedding
    return body
