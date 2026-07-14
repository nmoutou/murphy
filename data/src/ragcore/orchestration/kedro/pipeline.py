"""Le DAG d'ingestion — l'ordre du pipeline, exprimé par les dépendances de données.

Kedro ordonnance à partir des inputs/outputs des nœuds : il n'y a aucun ``join()``,
aucun ordre impératif. Deux arêtes portent tout le sens de cet ordre :

- **``force_drop_done`` → ``connect``** : ``connect`` prend ce signal en input, donc
  Kedro ne peut pas le lancer avant que ``forceDrop`` ait fini. Sans cette arête, on
  pourrait lire la source pendant qu'on efface les stores.

- **``ingestion_outcome`` → ``resolveRelations``** : c'est LA barrière phase-1/phase-2.
  La phase 2 écrit les arêtes, et une arête a besoin que ses deux nœuds existent. Tant
  que la phase 1 n'a pas fini pour *tous* les documents, l'outcome n'existe pas — donc
  Kedro ne lance pas la phase 2. La barrière est structurelle, pas un verrou.

Les objets runtime (``connector``, ``parser``, ``runner``, ``resolve_service``,
``pipeline_runtime``, les dépôts…) ne sont pas des paramètres : ce sont des
``MemoryDataset`` que ``TelemetryHooks.before_pipeline_run`` injecte au catalogue. Le
DAG les nomme, le hook les fournit.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline, node, pipeline

from .nodes.cleanup import cleanup_node
from .nodes.compute_idempotence import compute_idempotence_node
from .nodes.connect import connect_node
from .nodes.force_drop import force_drop_node
from .nodes.ingest import ingest_node
from .nodes.report import report_node
from .nodes.resolve_relations import resolve_relations_node

__all__ = ["create_ingestion_pipeline"]


def create_ingestion_pipeline() -> Pipeline:
    """cleanup → forceDrop → connect → computeIdempotence → ingest → resolve → report."""
    return pipeline(
        [
            node(
                func=cleanup_node,
                inputs=[
                    "params:maintenance.cache_paths",
                    "pipeline_context",
                    "telemetry",
                ],
                outputs="cleanup_results",
                name="cleanup",
            ),
            node(
                func=force_drop_node,
                inputs=[
                    "doc_repo",
                    "manifest_repo",
                    "graph_repo",
                    "vector_repo",
                    "params:exportation.mongodb",
                    "params:exportation.neo4j",
                    "params:exportation.qdrant",
                    "pipeline_context",
                    "telemetry",
                    "pipeline_runtime",
                ],
                outputs="force_drop_done",
                name="forceDrop",
            ),
            node(
                func=connect_node,
                inputs=[
                    "connector",
                    "pipeline_context",
                    "telemetry",
                    "pipeline_runtime",
                    # signal-only : impose forceDrop AVANT connect (arête du DAG).
                    "force_drop_done",
                ],
                outputs="raw_documents",
                name="connect",
            ),
            node(
                func=compute_idempotence_node,
                inputs=[
                    "raw_documents",
                    "parser",
                    "manifest_repo",
                    "pipeline_context",
                    "telemetry",
                    "pipeline_runtime",
                ],
                outputs=["to_process", "to_skip"],
                name="computeIdempotence",
            ),
            node(
                func=ingest_node,
                inputs=["to_process", "runner", "pipeline_context"],
                outputs="ingestion_outcome",
                name="ingest",
            ),
            node(
                func=resolve_relations_node,
                # ``ingestion_outcome`` en input = la barrière phase-1/phase-2.
                inputs=[
                    "ingestion_outcome",
                    "resolve_service",
                    "pipeline_runtime",
                    "pipeline_context",
                ],
                outputs="resolution_outcome",
                name="resolveRelations",
            ),
            node(
                func=report_node,
                inputs=[
                    "ingestion_outcome",
                    "resolution_outcome",
                    "to_skip",
                    # Le node POUSSE les stats des workers vers le hook. Kedro libère les
                    # MemoryDataset dès leur dernier lecteur : après ce node, plus
                    # personne ne peut relire `ingestion_outcome`.
                    "run_stats_sink",
                ],
                outputs="run_report",
                name="report",
            ),
        ]
    )
