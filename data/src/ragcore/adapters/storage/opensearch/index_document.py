"""Le corps d'un document OpenSearch, construit depuis le document parsé."""

from collections.abc import Iterable, Mapping
from typing import Any

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.search_content import IndexedPassage, SearchContent

__all__ = ["build_index_document"]

# Les `TITRE_TM` du même `<CONTEXTE>` titrent des subdivisions du texte, pas le texte
_PARENT_TEXT_KIND = "TITRE_TXT"


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
    parent_titles = _parent_text_titles(parsed.structure.get("context", []))
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


def _parent_text_titles(context: Iterable[Mapping[str, Any]]) -> list[str]:
    """Un titre par période, souvent le même : sans doublon, dans l'ordre du XML."""
    labels = (
        ancestor.get("label", "")
        for ancestor in context
        if ancestor.get("kind") == _PARENT_TEXT_KIND
    )
    return list(dict.fromkeys(label for label in labels if label))
