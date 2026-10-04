"""Nœud de la phase 1 : lance ``IngestionRunner``. Son ``IngestionOutcome`` alimente la
phase 2, et cette arête du DAG est la barrière entre les deux.
"""

from __future__ import annotations

from ragcore.adapters.storage.opensearch.search_index import OpenSearchSearchIndex
from ragcore.application.ingestion_runner import IngestionOutcome, IngestionRunner
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import ParsedDocument
from ragcore.core.ports.runtime import AsyncRuntime

__all__ = ["ingest_node"]


def ingest_node(
    to_process: list[ParsedDocument],
    runner: IngestionRunner,
    search_index: OpenSearchSearchIndex,
    pipeline_context: PipelineContext,
    pipeline_runtime: AsyncRuntime,
) -> IngestionOutcome:
    """L'index n'est pas rafraîchi pendant l'écriture. ``finally`` : un run en échec ne
    doit pas laisser un index qui ne publie plus rien."""
    pipeline_runtime.run(search_index.suspend_refresh())
    try:
        return runner.run(to_process, pipeline_context)
    finally:
        pipeline_runtime.run(search_index.resume_refresh())
