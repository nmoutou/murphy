"""Les problèmes d'un run d'ingestion : chacun devient une ligne de ``MURPHY_PROBLEMS``
(ADR-036)."""

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict

from .collision_record import CollisionRecord
from .enums import SourceName

__all__ = ["CopyStamp", "FileProblem", "Problem", "SupersededCopy"]


class CopyStamp(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    """Absolu."""
    mtime_ns: int


class SupersededCopy(BaseModel):
    """Une copie d'une racine que l'arbitrage a écartée pour une plus récente : une par
    copie écartée."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    identifier: str
    root: str
    kept: CopyStamp
    discarded: CopyStamp


FileProblem: TypeAlias = SupersededCopy
"""Ce que le connecteur écarte, en détail."""

Problem: TypeAlias = CollisionRecord | FileProblem
