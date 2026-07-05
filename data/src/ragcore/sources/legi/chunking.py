from ragcore.core.models import Chunk, ParsedDocument


class LegiChunker:
    name = "legi_structural"

    def __init__(self, max_chunk_size: int = 1000, overlap: int = 100) -> None:
        self._max_chunk_size = max_chunk_size
        self._overlap = overlap

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        chunks = self._structural_chunks(document)
        if not chunks:
            chunks = self._fixed_size_chunks(document)
        return chunks

    def _structural_chunks(self, document: ParsedDocument) -> list[Chunk]:
        """Découpe selon la structure (articles, alinéas)."""
        sections = document.structure.get("sections", [])
        if not sections:
            return []

        chunks = []
        ordinal = 0
        for section in sections:
            path = section.get("path", [])
            text = section.get("text", "")
            if not text.strip():
                continue
            char_start = document.content.find(text)
            char_end = char_start + len(text) if char_start >= 0 else len(text)
            chunks.append(
                Chunk(
                    chunk_id=f"{document.identifier.raw}_{ordinal:04d}",
                    parent_identifier=document.identifier,
                    owner_id=document.owner_id,
                    ordinal=ordinal,
                    text=text,
                    structural_path=path,
                    char_start=max(0, char_start),
                    char_end=char_end,
                    metadata=document.metadata,
                )
            )
            ordinal += 1
        return chunks

    def _fixed_size_chunks(self, document: ParsedDocument) -> list[Chunk]:
        """Fallback : découpe à taille fixe avec chevauchement."""
        text = document.content
        chunks = []
        ordinal = 0
        start = 0
        while start < len(text):
            end = min(start + self._max_chunk_size, len(text))
            chunk_text = text[start:end]
            chunks.append(
                Chunk(
                    chunk_id=f"{document.identifier.raw}_{ordinal:04d}",
                    parent_identifier=document.identifier,
                    owner_id=document.owner_id,
                    ordinal=ordinal,
                    text=chunk_text,
                    structural_path=[],
                    char_start=start,
                    char_end=end,
                    metadata=document.metadata,
                )
            )
            ordinal += 1
            start += self._max_chunk_size - self._overlap
        return chunks
