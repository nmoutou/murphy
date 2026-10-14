from __future__ import annotations

from pathlib import Path

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.document import RawDocument
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort, WorkerTelemetry
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_UNREADABLE,
)
from ragcore.core.statistics_measures import (
    FACETS,
    STAGE_PHASE1,
    XML_BYTES,
    document_measure,
)
from ragcore.core.telemetry_events import (
    DOCUMENT_FETCHED,
    DOCUMENT_UNREADABLE,
    DOCUMENT_VERSION_SKIPPED,
)
from ragcore.orchestration.kedro.stage_clock import StageClock

# Une raison absente d'ici lève `KeyError` plutôt que de finir dans un fourre-tout
_SKIP_EVENT_BY_REASON = {
    REASON_EXPORT_ARTIFACT: DOCUMENT_VERSION_SKIPPED,
    REASON_UNREADABLE: DOCUMENT_UNREADABLE,
}


def connect_node(
    connector: BaseConnector,
    pipeline_context: PipelineContext,
    telemetry: WorkerTelemetry,
    pipeline_runtime: AsyncRuntime,
    stage_clock: StageClock,
    nuke_done: dict[str, bool],
) -> list[RawDocument]:
    del nuke_done  # simple signal : nukeAll tourne avant connect

    async def _fetch() -> list[RawDocument]:
        return [doc async for doc in connector.fetch_all()]

    with stage_clock.stage(STAGE_PHASE1):
        documents = pipeline_runtime.run(_fetch())
        for document in documents:
            _measure(telemetry, document)

    _emit(telemetry, pipeline_context, DOCUMENT_FETCHED, {"count": len(documents)})

    # Les écartés, hors `document.fetched` : un compteur par raison, hors équation
    for reason, count in connector.skipped.items():
        _emit(
            telemetry,
            pipeline_context,
            _SKIP_EVENT_BY_REASON[reason],
            {"count": count},
        )
    return documents


def _measure(telemetry: WorkerTelemetry, document: RawDocument) -> None:
    files = document.payload["files"]
    sizes = {
        XML_BYTES: sum(Path(file).stat().st_size for file in files),
        FACETS: len(files),
    }
    for name, size in sizes.items():
        telemetry.record_measure(
            document_measure(document.source, name), size, document.source_document_id
        )


def _emit(
    telemetry: TelemetryPort,
    context: PipelineContext,
    event_type: str,
    payload: dict[str, object],
) -> None:
    telemetry.emit(
        build_event(
            event_type=event_type,
            run_id=context.run_id,
            source=context.source,
            payload=payload,
        )
    )
