"""Le DAG d'ingestion — l'ordre du pipeline, exprimé par les dépendances de données.

Kedro ordonnance à partir des inputs/outputs des nœuds : il n'y a aucun ``join()``,
aucun ordre impératif. Deux arêtes portent tout le sens de cet ordre :

- **``nuke_done`` → ``connect``** : ``connect`` prend ce signal en input, donc
  Kedro ne peut pas le lancer avant que ``nukeAll`` ait fini. Sans cette arête, on
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

from kedro.pipeline import Node, Pipeline, node, pipeline

from .nodes.connect import connect_node
from .nodes.ingest import ingest_node
from .nodes.nuke_all import nuke_all_node
from .nodes.parse_documents import parse_documents_node
from .nodes.report import report_node
from .nodes.resolve_relations import resolve_relations_node

__all__ = ["create_ingestion_pipeline"]


def create_ingestion_pipeline() -> Pipeline:
    """nukeAll → connect → parseDocuments → ingest → resolve → report."""
    return pipeline(
        [
            _nuke_all(),
            _connect(),
            _parse_documents(),
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
            "vector_repo",
            # Déjà arbitré par le plan du run : refusé hors dev avant tout nœud.
            "nuke_all",
            "pipeline_context",
            "telemetry",
            "pipeline_runtime",
        ],
        outputs="nuke_done",
        name="nukeAll",
    )


def _connect() -> Node:
    return node(
        func=connect_node,
        inputs=[
            "connector",
            "pipeline_context",
            "telemetry",
            "pipeline_runtime",
            # signal-only : impose nukeAll AVANT connect (arête du DAG).
            "nuke_done",
        ],
        outputs="raw_documents",
        name="connect",
    )


def _parse_documents() -> Node:
    return node(
        func=parse_documents_node,
        inputs=[
            "raw_documents",
            "parser",
            "pipeline_context",
            "telemetry",
            # Le curseur `dev.skip_unconfigured`, arbitré par le plan du run :
            # appliqué au site de parse, juste avant que le document parte à l'ingestion.
            "skip_unconfigured",
        ],
        outputs=["to_process", "to_skip"],
        name="parseDocuments",
    )


def _ingest() -> Node:
    return node(
        func=ingest_node,
        inputs=["to_process", "runner", "pipeline_context"],
        outputs="ingestion_outcome",
        name="ingest",
    )


def _resolve_relations() -> Node:
    return node(
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
    )


def _report() -> Node:
    return node(
        func=report_node,
        inputs=[
            "ingestion_outcome",
            "resolution_outcome",
            "to_skip",
            # Le node POUSSE les stats des workers vers l'agrégat du run. Kedro libère
            # les MemoryDataset dès leur dernier lecteur : après ce node, plus personne
            # ne peut relire `ingestion_outcome`.
            "run_stats_sink",
        ],
        outputs="run_report",
        name="report",
    )
