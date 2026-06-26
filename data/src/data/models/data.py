"""Data models for the data pipeline."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentRecord:
    """Document canonique du pipeline.

    Utilisé de rawDocuments à readyDocuments.
    Le champ metadata évolue entre les phases :
    - forme standardisée dans standardDocuments et cleanDocuments ;
    - forme finale stable dans readyDocuments et tous les datasets aval.
    """
    eli: str
    texts: str|list[str]
    metadata: dict[str, Any]
    relations: list[tuple[str, str, str]]


@dataclass
class RelationRecord:
    """Relation normalisée entre documents.

    Produite par buildRelations à partir de readyDocuments.
    Invariants : relationType en minuscules, mappings appliqués,
    relations filtrées, réduction transitive appliquée.
    """
    sourceEli: str
    targetEli: str
    relationType: str

    def to_dict(self):
        return dict(
            sourceEli=self.sourceEli,
            targetEli=self.targetEli,
            relationType=self.relationType,
        )


@dataclass
class TokenizedDocumentRecord:
    """Document tokenisé pour préparation au chunking.

    Produit par tokenizeContent à partir de readyDocuments.
    Le contenu doit être non vide ; les métadonnées sont celles
    de readyDocuments, inchangées.
    """
    eli: str
    content: str
    tokens: list[Any]
    metadata: dict[str, Any]


@dataclass
class ChunkRecord:
    """Chunk textuel, éventuellement vectorisé.

    Produit par buildChunks (embedding is None)
    puis enrichi par embedChunks (embedding non nul).
    """
    chunkId: str
    eli: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None
