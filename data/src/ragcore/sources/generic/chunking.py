"""Le chunker structurel, commun à toutes les sources : il ne lit que
``document.content`` et ``document.structure["sections"]``.

Ses offsets reposent sur un invariant du parser : chaque section est un morceau
littéral de ``content``, dans le même ordre.
"""

from dataclasses import dataclass

from ragcore.core.models import Chunk, ParsedDocument
from ragcore.core.models.processing import ChunkingConfig

__all__ = ["StructuralChunker"]


@dataclass(frozen=True)
class _Span:
    path: list[str]
    text: str
    char_start: int
    char_end: int


class StructuralChunker:
    name = "structural"

    def __init__(self, config: ChunkingConfig) -> None:
        """``config`` garantit ``overlap_chars < max_chars`` : le curseur avance."""
        self._max_chars = config.max_chars
        self._overlap_chars = config.overlap_chars

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """La structure dit où couper, la taille jusqu'où aller : on ne coupe jamais à
        travers un bloc, et on ne dépasse jamais la taille dans un bloc.

        Un document sans contenu (une ``SECTION_TA``, nœud de structure) ne rend aucun
        chunk.
        """
        if not document.content.strip():
            return []

        blocks = self._blocks(document)
        chunks: list[Chunk] = []
        ordinal = 0

        for path, text, offset in blocks:
            for start, end in _windows(len(text), self._max_chars, self._overlap_chars):
                span = _Span(path, text[start:end], offset + start, offset + end)
                chunks.append(self._chunk(document, ordinal, span))
                ordinal += 1

        return chunks

    def _blocks(self, document: ParsedDocument) -> list[tuple[list[str], str, int]]:
        """``(chemin, texte, offset dans le contenu)``. Sans section, le document entier
        est un bloc.

        Le curseur ne recule jamais : deux blocs au texte identique reçoivent des offsets
        différents.
        """
        sections = document.structure.get("sections", [])
        if not sections:
            return [([], document.content, 0)]

        blocks: list[tuple[list[str], str, int]] = []
        cursor = 0

        for section in sections:
            text = section.get("text", "")
            if not text.strip():
                continue

            start = document.content.find(text, cursor)
            if start < 0:
                # Invariant du parser rompu : mieux vaut aucun offset qu'un faux
                continue

            cursor = start + len(text)
            blocks.append((list(section.get("path", [])), text, start))

        return blocks or [([], document.content, 0)]

    def _chunk(self, document: ParsedDocument, ordinal: int, span: _Span) -> Chunk:
        return Chunk(
            # Dérivé de l'identifiant du parent : deux workers ne touchent jamais le
            # même chunk
            chunk_id=f"{document.identifier.raw}_{ordinal:04d}",
            parent_identifier=document.identifier,
            document_type=document.document_type,
            nature=document.nature,
            ordinal=ordinal,
            text=span.text,
            tag_path=span.path,
            char_start=span.char_start,
            char_end=span.char_end,
            metadata=document.metadata,
        )


def _windows(length: int, size: int, overlap: int) -> list[tuple[int, int]]:
    """Les fenêtres ``(début, fin)`` couvrant ``length``, avec chevauchement.

    Arrêt dès qu'une fenêtre atteint la fin : avec un fort chevauchement, les suivantes
    seraient entièrement contenues dans la précédente.
    """
    if length <= size:
        return [(0, length)]

    step = size - overlap
    windows: list[tuple[int, int]] = []
    for start in range(0, length, step):
        end = min(start + size, length)
        windows.append((start, end))
        if end == length:
            break
    return windows
