"""Une clé de métadonnée qui a reçu plusieurs valeurs distinctes (ADR-025).

Toutes les occurrences sont gardées, doublons compris, dans l'ordre déclaré : rang de la
facette, puis ordre du document.
"""

from pydantic import BaseModel, ConfigDict

from .enums import SourceName

__all__ = ["Collision", "CollisionValue"]


class CollisionValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: str
    source_file: str
    """Vide s'il est inconnu."""


class Collision(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: SourceName
    identifier: str
    key: str
    values: tuple[CollisionValue, ...]

    def source_files(self) -> tuple[str, ...]:
        """Distincts, dans l'ordre des valeurs."""
        return tuple(dict.fromkeys(value.source_file for value in self.values))
