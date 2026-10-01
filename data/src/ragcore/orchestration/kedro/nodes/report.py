"""Nœud terminal : le bilan du run, composé des deux phases, sans I/O.

C'est aussi le seul point de remontée des stats des workers vers l'agrégateur du run :
Kedro libère ``ingestion_outcome`` dès son dernier lecteur, ce nœud, et le hook ne
pourrait plus le relire. Limite : si le pipeline casse avant lui, le bilan du run
``failed`` n'a que les compteurs du processus principal.

Un échec partiel ne fait pas échouer le run : le document est compté et nommé dans
``failures``.
"""

from __future__ import annotations

from typing import Any, Protocol

from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import ResolutionOutcome
from ragcore.core.models.run_stats import RunStats

__all__ = ["RunStatsSink", "report_node"]


class RunStatsSink(Protocol):
    """L'agrégateur du run, posé au catalogue par le hook."""

    def absorb(self, stats: RunStats) -> None: ...


def report_node(
    ingestion_outcome: IngestionOutcome,
    resolution_outcome: ResolutionOutcome,
    to_skip: list[str],
    run_stats_sink: RunStatsSink,
) -> dict[str, Any]:
    stats = ingestion_outcome.stats

    # Pas la phase 2 : elle émet déjà sur la télémétrie du hook, elle compterait double
    run_stats_sink.absorb(ingestion_outcome.stats)

    return {
        "documents_written": len(ingestion_outcome.written_node_ids),
        "documents_skipped": len(to_skip),
        "documents_failed": len(ingestion_outcome.failures),
        # (identifiant, message) : un échec anonyme ne se rejoue pas
        "failures": list(ingestion_outcome.failures),
        "relations_extracted": len(ingestion_outcome.relations),
        "relations_written": resolution_outcome.written_count,
        "relations_pending": resolution_outcome.pending_count,
        "relations_reduced": resolution_outcome.reduced_count,
        "relations_promoted": resolution_outcome.promoted_count,
        # Vide = le vocabulaire de la source a tout couvert
        "unknowns": {
            category: {value: tally.model_dump() for value, tally in tallies.items()}
            for category, tallies in stats.unknowns.items()
        },
        "collisions": {
            key: tally.model_dump() for key, tally in stats.collisions.items()
        },
    }
