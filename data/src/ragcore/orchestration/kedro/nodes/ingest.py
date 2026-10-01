"""Nœud de la phase 1 : lance ``IngestionRunner``. Son ``IngestionOutcome`` alimente la
phase 2, et cette arête du DAG est la barrière entre les deux.
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
    return runner.run(to_process, pipeline_context)
