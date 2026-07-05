from __future__ import annotations

from ragcore.application.pipeline_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.telemetry_events import DOCUMENT_FETCHED
from ragcore.core.models.document import RawDocument
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.telemetry import TelemetryPort

from ._async_utils import run_async


def connect_node(
    connector: BaseConnector,
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
    force_drop_done: dict[str, bool],
) -> list[RawDocument]:
    """Fetch all raw documents from the source connector."""
    del force_drop_done  # signal-only input: ensures forceDrop runs before connect

    async def _fetch() -> list[RawDocument]:
        return [doc async for doc in connector.fetch_all(pipeline_context.owner_id)]

    documents = run_async(_fetch())

    telemetry.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=pipeline_context.run_id,
            owner_id=pipeline_context.owner_id,
            source=pipeline_context.source,
            payload={"count": len(documents)},
        )
    )
    return documents
