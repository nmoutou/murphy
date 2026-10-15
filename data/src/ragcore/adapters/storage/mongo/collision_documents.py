"""Les documents de ``collisions`` : un par source et par run, découpé en parties
numérotées quand ses détails dépassent la limite d'un document Mongo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import bson

from ragcore.core.models.run_collisions import SourceCollisions

__all__ = ["PART_BUDGET_BYTES", "source_documents"]

PART_BUDGET_BYTES = 15 * 1024 * 1024
"""Sous les 16 Mio d'un document Mongo : la marge couvre l'enveloppe et les comptes."""

_Detail = tuple[str, dict[str, Any]]
"""La raison, et le détail."""


def source_documents(
    header: Mapping[str, Any],
    collisions: SourceCollisions,
    budget_bytes: int = PART_BUDGET_BYTES,
) -> list[dict[str, Any]]:
    """``header`` porte l'identité du document (run, source). Chaque partie répète les
    comptes de la source entière ; les détails s'y répartissent dans l'ordre."""
    counts = {reason: len(records) for reason, records in collisions.items()}
    details = [
        (reason, record.to_detail())
        for reason, records in collisions.items()
        for record in records
    ]
    parts = _split(details, budget_bytes)
    return [
        {
            **header,
            "part": number,
            "parts": len(parts),
            "collisions": _by_reason(counts, part),
        }
        for number, part in enumerate(parts, start=1)
    ]


def _split(details: list[_Detail], budget_bytes: int) -> list[list[_Detail]]:
    """Une partie reçoit au moins un détail, même trop gros : Mongo refusera le
    document plutôt que de boucler ici."""
    parts: list[list[_Detail]] = [[]]
    used = 0
    for detail in details:
        size = len(bson.encode(detail[1]))
        if parts[-1] and used + size > budget_bytes:
            parts.append([])
            used = 0
        parts[-1].append(detail)
        used += size
    return parts


def _by_reason(
    counts: Mapping[str, int], part: list[_Detail]
) -> dict[str, dict[str, Any]]:
    return {
        reason: {
            "count": count,
            "details": [detail for owner, detail in part if owner == reason],
        }
        for reason, count in counts.items()
    }
