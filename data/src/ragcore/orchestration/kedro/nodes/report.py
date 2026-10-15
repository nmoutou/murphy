"""Nœud terminal : le bilan du run, composé des deux phases, sans I/O.

Un échec partiel ne fait pas échouer le run : le document est compté et nommé dans
``failures``.
"""

from __future__ import annotations

from typing import Any

from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import ResolutionOutcome

__all__ = ["report_node"]


def report_node(
    ingestion_outcome: IngestionOutcome,
    resolution_outcome: ResolutionOutcome,
    to_skip: list[str],
) -> dict[str, Any]:
    stats = ingestion_outcome.stats

    return {
        "documents_written": len(ingestion_outcome.written_node_ids),
        "documents_skipped": len(to_skip),
        "documents_failed": len(ingestion_outcome.failures),
        # (identifiant, message) : un échec anonyme ne se rejoue pas
        "failures": list(ingestion_outcome.failures),
        "relations_extracted": resolution_outcome.extracted_count,
        "relations_written": resolution_outcome.written_count,
        "relations_pending": resolution_outcome.pending_count,
        "relations_reduced": resolution_outcome.reduced_count,
        "relations_promoted": resolution_outcome.promoted_count,
        # Vide = le vocabulaire de la source a tout couvert
        "unknowns": {
            category: {value: tally.model_dump() for value, tally in tallies.items()}
            for category, tallies in stats.unknowns.items()
        },
        "collisions": dict(stats.collisions),
        "invalidations": dict(stats.invalidations),
    }
