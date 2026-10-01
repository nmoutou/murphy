"""Nœud report — le bilan du run, assemblé à partir des deux phases.

C'est le nœud terminal du DAG. Il ne fait aucune I/O : il compose une donnée à partir
des deux outcomes (phase 1 + phase 2) et des documents écartés au parsing.

**Ce nœud est aussi le seul point de remontée des stats des workers.** Il reçoit
``ingestion_outcome.stats`` — la fusion des ``RunStats`` de tous les workers — et la
POUSSE dans le ``RunStatsSink`` (l'agrégateur du run, que le hook finalise). Sans
cela, le hook ne finalisait que les compteurs du process principal, qui ne voit **jamais une compensation** : le
compteur restait nul et ``_status_from`` rendait **toujours** ``ok``.

Pourquoi ici et pas dans le hook : ``ingestion_outcome`` est un ``MemoryDataset``, et
Kedro le **libère** dès son dernier lecteur — ce nœud. Un ``catalog.load()`` en
``after_pipeline_run`` tombe donc sur un dataset vide. Le DAG doit pousser ; le hook ne
peut pas tirer.

⚠️ **Limite assumée :** ce nœud est terminal. Si le pipeline casse AVANT lui, les stats
des workers ne remontent pas et ``on_pipeline_error`` ne persiste que les compteurs du
process principal. Le run est alors ``failed`` — ce qui reste vrai — mais son bilan est
pauvre. Le corriger demanderait un point de remontée par phase, pas un seul en fin de DAG.

**Un échec partiel NE fait PAS échouer le run.** Un document dont la saga a échoué (et
a compensé) est compté et NOMMÉ dans ``failures`` — il n'arrête pas le corpus, et il
n'est pas perdu en silence. C'est l'esprit « rien en silence » : la complétude du run
se LIT dans le report, elle ne se décrète pas par une exception. La saturation du
vocabulaire, elle aussi, se lit ici (``unknowns`` vide = la source a tout couvert).
"""

from __future__ import annotations

from typing import Any, Protocol

from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import ResolutionOutcome
from ragcore.core.models.run_stats import RunStats

__all__ = ["RunStatsSink", "report_node"]


class RunStatsSink(Protocol):
    """Ce qui reçoit l'agrégat des phases : l'agrégateur du run (``RunStatsAggregator``),
    posé au catalogue par le hook. Le node ne connaît ni Kedro ni le hook : le DAG pousse
    une donnée, il n'appelle pas un orchestrateur."""

    def absorb(self, stats: RunStats) -> None: ...


def report_node(
    ingestion_outcome: IngestionOutcome,
    resolution_outcome: ResolutionOutcome,
    to_skip: list[str],
    run_stats_sink: RunStatsSink,
) -> dict[str, Any]:
    """Compose le bilan du run — documents, relations, échecs, inconnus."""
    stats = ingestion_outcome.stats

    # L'agrégat des WORKERS remonte ICI, et seulement ici. `ingestion_outcome` est un
    # `MemoryDataset` que Kedro LIBÈRE dès son dernier lecteur — ce node. Après lui, plus
    # personne ne peut le relire : c'est donc lui, et lui seul, qui peut le transmettre.
    #
    # ⚠️ La phase 2 n'est PAS poussée : `ResolveRelationsService` tourne sur la boucle du
    # hook et émet donc déjà sur SA télémétrie — ses compteurs sont dans l'agrégat. Les
    # pousser ici les compterait DEUX fois (mesuré : `relation.pending` à 38 064 pour
    # 19 032 réelles). Seuls les workers ont un agrégat orphelin ; eux seuls remontent.
    run_stats_sink.absorb(ingestion_outcome.stats)

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
        "unknowns": {
            category: {value: tally.model_dump() for value, tally in tallies.items()}
            for category, tallies in stats.unknowns.items()
        },
    }
