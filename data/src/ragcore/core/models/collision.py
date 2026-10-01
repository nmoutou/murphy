"""Collision — une clé de métadonnée qui a reçu plusieurs valeurs distinctes (ADR-049).

Le parser la constate, le site de parse la compte au bilan. Elle garde TOUTES les
occurrences, doublons compris, dans l'ordre déclaré (rang de la facette, puis ordre du
document).
"""

from pydantic import BaseModel, ConfigDict

from .enums import SourceName

__all__ = ["Collision", "CollisionValue"]


class CollisionValue(BaseModel):
    """Une occurrence de la clé : sa valeur, et d'où elle vient."""

    model_config = ConfigDict(frozen=True)

    value: str
    tag: str
    """La balise qui la porte (``URL``)."""
    path: str
    """Son chemin depuis la racine de la facette (``TEXTELR/META/META_COMMUN/URL``)."""
    source_file: str
    """Le fichier de la facette, vide s'il est inconnu."""
    root: str
    """La racine de la facette (``TEXTELR``)."""


class Collision(BaseModel):
    """Une clé d'un document, et toutes ses occurrences."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    identifier: str
    key: str
    values: tuple[CollisionValue, ...]
