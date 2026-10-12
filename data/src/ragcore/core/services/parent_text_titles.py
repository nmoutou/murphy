"""Les titres du texte parent d'un document : Mongo et OpenSearch les écrivent tous deux."""

from ragcore.core.models.document import ParsedDocument

__all__ = ["parent_text_titles"]

# Les `TITRE_TM` du même `<CONTEXTE>` titrent des subdivisions du texte, pas le texte
_PARENT_TEXT_KIND = "TITRE_TXT"


def parent_text_titles(document: ParsedDocument) -> list[str]:
    """Un titre par période, souvent le même : sans doublon, dans l'ordre du XML."""
    labels = (
        ancestor.get("label", "")
        for ancestor in document.structure.get("context", [])
        if ancestor.get("kind") == _PARENT_TEXT_KIND
    )
    return list(dict.fromkeys(label for label in labels if label))
