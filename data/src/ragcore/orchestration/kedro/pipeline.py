"""Le DAG d'ingestion : l'ordre vient des seules dépendances de données.

- ``nuke_done`` → ``ingest`` : la source n'est pas lue pendant l'effacement ;
- ``ingestion_outcome`` → ``resolveRelations`` : la barrière entre les phases, une
  arête ayant besoin que ses deux nœuds existent.

Les objets vivants (connecteur, dépôts, runtime…) sont des ``MemoryDataset`` que le hook
pose au catalogue : le DAG les nomme, le hook les fournit.
"""

from __future__ import annotations

from kedro.pipeline import Node, Pipeline, node, pipeline

from .nodes.ingest import ingest_node
from .nodes.nuke_all import nuke_all_node
from .nodes.report import report_node
from .nodes.resolve_relations import resolve_relations_node

__all__ = ["create_ingestion_pipeline"]


def create_ingestion_pipeline() -> Pipeline:
    """nukeAll → ingest → resolve → report."""
    return pipeline(
        [
            _nuke_all(),
            _ingest(),
            _resolve_relations(),
            _report(),
        ]
    )


def _nuke_all() -> Node:
    return node(
        func=nuke_all_node,
        inputs=[
            "doc_repo",
            "graph_repo",
            "search_index",
            # Déjà arbitré par le plan du run : `False` hors dev
            "nuke_all",
            "pipeline_runtime",
        ],
        outputs="nuke_done",
        name="nukeAll",
    )


def _ingest() -> Node:
    return node(
        func=ingest_node,
        inputs=[
            "connector",
            "parser",
            "runner",
            "search_index",
            "pipeline_context",
            "telemetry",
            "pipeline_runtime",
            "skip_unconfigured",
            "run_sink",
            "stage_clock",
            # Simple signal : nukeAll avant la lecture
            "nuke_done",
        ],
        outputs=["ingestion_outcome", "to_skip"],
        name="ingest",
    )


def _resolve_relations() -> Node:
    return node(
        func=resolve_relations_node,
        # `ingestion_outcome` en input : la barrière entre les phases
        inputs=[
            "ingestion_outcome",
            "resolve_service",
            "pipeline_runtime",
            "pipeline_context",
            "stage_clock",
        ],
        outputs="resolution_outcome",
        name="resolveRelations",
    )


def _report() -> Node:
    return node(
        func=report_node,
        inputs=[
            "ingestion_outcome",
            "resolution_outcome",
            "to_skip",
        ],
        outputs="run_report",
        name="report",
    )
