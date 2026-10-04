from pydantic import BaseModel, ConfigDict

from .chunk import Chunk


class IndexedPassage(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk
    embedding: list[float] | None = None
    """``None`` quand l'embedding est coupé (ADR-012) : le passage reste cherchable par
    son texte."""


class SearchContent(BaseModel):
    """Ce que l'index de recherche reçoit d'un document, en plus du document parsé."""

    model_config = ConfigDict(frozen=True)

    passages: tuple[IndexedPassage, ...] = ()
    title_embedding: list[float] | None = None
    """Seulement pour un document sans passage (ADR-029)."""
