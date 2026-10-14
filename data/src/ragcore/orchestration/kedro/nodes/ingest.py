"""Nœud de la phase 1 (ADR-034 §2) : lecture, parse et ingestion en flux. La lecture et
le parse tournent dans ce thread et alimentent la file des workers ; aucune étape ne
matérialise le corpus. Son ``IngestionOutcome`` alimente la phase 2, et cette arête du
DAG est la barrière entre les deux.
"""

from __future__ import annotations

from typing import Protocol

from ragcore.adapters.storage.opensearch.search_index import OpenSearchSearchIndex
from ragcore.application.document_parsing import DocumentParsing
from ragcore.application.ingestion_runner import (
    IngestionOutcome,
    IngestionRunner,
    WorkerResultsSink,
)
from ragcore.application.run_context import PipelineContext
from ragcore.application.source_reading import InventorySink, SourceReading
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.parser import BaseParser
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.statistics_measures import STAGE_DISCOVERY, STAGE_PHASE1
from ragcore.orchestration.kedro.stage_clock import StageClock

__all__ = ["RunSink", "ingest_node"]


class RunSink(WorkerResultsSink, InventorySink, Protocol):
    """Les agrégats du run, que le hook clôt."""


def ingest_node(
    connector: BaseConnector,
    parser: BaseParser,
    runner: IngestionRunner,
    search_index: OpenSearchSearchIndex,
    pipeline_context: PipelineContext,
    telemetry: WorkerTelemetry,
    pipeline_runtime: AsyncRuntime,
    skip_unconfigured: bool,
    run_sink: RunSink,
    stage_clock: StageClock,
    nuke_done: dict[str, bool],
) -> tuple[IngestionOutcome, list[str]]:
    """Rend aussi les documents rejetés au parse.

    L'index n'est pas rafraîchi pendant l'écriture. ``finally`` : un run en échec ne
    doit pas laisser un index qui ne publie plus rien, et compte ce qu'il a lu. Seul un
    run arrivé au bout est fusionné."""
    del nuke_done  # simple signal : nukeAll tourne avant la lecture

    reading = SourceReading(connector, pipeline_context, telemetry)
    with stage_clock.stage(STAGE_DISCOVERY):
        expected = reading.discover(run_sink)
    parsing = DocumentParsing(parser, pipeline_context, telemetry, skip_unconfigured)
    documents = parsing.parse_all(reading.documents())

    with stage_clock.stage(STAGE_PHASE1):
        pipeline_runtime.run(search_index.suspend_refresh())
        try:
            outcome = runner.run(documents, pipeline_context, run_sink, expected)
        finally:
            pipeline_runtime.run(search_index.resume_refresh())
            reading.declare_counts()
        pipeline_runtime.run(search_index.force_merge())
    return outcome, parsing.skipped
