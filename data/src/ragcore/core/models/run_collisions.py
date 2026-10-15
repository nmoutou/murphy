"""Les collisions d'un run, en détail : le pendant de ``RunStats.collisions``, qui n'en
garde que les comptes."""

from __future__ import annotations

from dataclasses import dataclass

from .collision_record import CollisionRecord
from .enums import SourceName

__all__ = ["RunCollisions", "SourceCollisions"]

SourceCollisions = dict[str, tuple[CollisionRecord, ...]]
"""Raison -> détails."""


@dataclass(frozen=True)
class RunCollisions:
    records: tuple[CollisionRecord, ...] = ()

    def by_source(self) -> dict[SourceName, SourceCollisions]:
        """Triés par (identifiant, clé) : un run rejoué écrit les mêmes documents, quel
        que soit l'ordre de lecture."""
        grouped: dict[SourceName, dict[str, list[CollisionRecord]]] = {}
        for record in self.records:
            reasons = grouped.setdefault(record.source, {})
            reasons.setdefault(record.reason, []).append(record)
        return {
            source: {
                reason: tuple(sorted(found, key=_order))
                for reason, found in sorted(reasons.items())
            }
            for source, reasons in sorted(grouped.items())
        }


def _order(record: CollisionRecord) -> tuple[str, str, tuple[str, ...]]:
    return record.identifier, record.key, record.files
