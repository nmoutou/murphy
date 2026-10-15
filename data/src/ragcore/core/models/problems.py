"""Les problèmes d'un run d'ingestion : chacun devient une ligne de ``MURPHY_PROBLEMS``
(ADR-036)."""

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict

from .collision_record import CollisionRecord
from .enums import SourceName

__all__ = [
    "CopyStamp",
    "FileProblem",
    "MismatchedFile",
    "Problem",
    "SupersededCopy",
    "UnreadableFile",
]


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


class UnreadableFile(BaseModel):
    """Un fichier dont le XML ne se lit pas (tronqué, encodage cassé)."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    key: str
    """Le nom du fichier sans extension."""
    path: str
    error: str
    """Le message du parseur XML, avec sa ligne et sa colonne."""


class MismatchedFile(BaseModel):
    """Un fichier dont l'``<ID>`` n'est pas le nom (ADR-034 §1)."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    key: str
    path: str
    found_id: str | None
    """``None`` pour un fichier sans ``<ID>``."""


FileProblem: TypeAlias = SupersededCopy | UnreadableFile | MismatchedFile
"""Ce que le connecteur écarte, en détail."""

Problem: TypeAlias = CollisionRecord | FileProblem
