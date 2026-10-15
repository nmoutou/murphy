"""Les problèmes d'un run d'ingestion : chacun devient une ligne de ``MURPHY_PROBLEMS``
(ADR-036)."""

from typing import TypeAlias

from .collision_record import CollisionRecord

__all__ = ["Problem"]

Problem: TypeAlias = CollisionRecord
