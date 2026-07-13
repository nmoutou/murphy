"""Nœud report — le bilan du run, assemblé à partir des deux phases.

C'est le nœud terminal du DAG. Il ne fait aucune I/O : il compose une donnée à partir
des deux outcomes (phase 1 + phase 2) et des documents écartés au parsing. Le hook, en
``after_pipeline_run``, finalise l'agrégat des workers en ``RunSummary`` et le persiste ;
ce report est la vue lisible côté pipeline, et le point où l'on rend explicite ce qui,
sinon, resterait éparpillé entre trois outcomes.

**Un échec partiel NE fait PAS échouer le run.** Un document dont la saga a échoué (et
a compensé) est compté et NOMMÉ dans ``failures`` — il n'arrête pas le corpus, et il
n'est pas perdu en silence. C'est l'esprit « rien en silence » : la complétude du run
se LIT dans le report, elle ne se décrète pas par une exception. La saturation du
vocabulaire, elle aussi, se lit ici (``unknowns`` vide = la source a tout couvert).
"""

from __future__ import annotations

from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import ResolutionOutcome

__all__ = ["report_node"]


def report_node(
    ingestion_outcome: IngestionOutcome,
    resolution_outcome: ResolutionOutcome,
    to_skip: list[str],
) -> dict:
    """Compose le bilan du run — documents, relations, échecs, inconnus."""
    stats = ingestion_outcome.stats

    return {
        "documents_written": len(ingestion_outcome.written_node_ids),
        "documents_skipped": len(to_skip),
        "documents_failed": len(ingestion_outcome.failures),
        # (identifiant, message) — jamais un simple compte : un échec anonyme est un
        # échec qu'on ne pourra pas rejouer.
        "failures": list(ingestion_outcome.failures),
        "relations_extracted": len(ingestion_outcome.relations),
        "relations_written": resolution_outcome.written_count,
        "relations_pending": resolution_outcome.pending_count,
        "relations_reduced": resolution_outcome.reduced_count,
        "relations_promoted": resolution_outcome.promoted_count,
        # Vide = le vocabulaire de la source a tout couvert. Non vide = ce que le run
        # a vu sans savoir le nommer, prêt à enseigner la prochaine table.
        "unknowns": dict(stats.unknowns),
    }
