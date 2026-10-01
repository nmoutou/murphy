"""Nœud phase 1 — le pool d'ingestion, exprimé comme un nœud Kedro.

Le nœud est mince par principe : toute la logique du pool (partition par clé, N
runtimes isolés, réduction des agrégats, §11) vit dans ``IngestionRunner``. Le nœud
ne fait que le lancer et remonter son ``IngestionOutcome`` — de la DONNÉE, pas un
effet de bord de hook. C'est cette donnée que la phase 2 consomme, et l'arête du DAG
entre les deux est la barrière : Kedro ne lance pas ``resolveRelations`` avant que
``ingest`` ait fini pour *tous* les documents.
"""

from __future__ import annotations

from ragcore.application.ingestion_runner import IngestionOutcome, IngestionRunner
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import ParsedDocument

__all__ = ["ingest_node"]


def ingest_node(
    to_process: list[ParsedDocument],
    runner: IngestionRunner,
    pipeline_context: PipelineContext,
) -> IngestionOutcome:
    """Ingère les documents parsés en parallèle et rend l'outcome de la phase 1."""
    return runner.run(to_process, pipeline_context)
