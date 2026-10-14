"""Lit la source : la passe 1 de chaque connecteur, puis la passe 2 drainée dans une
liste."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter
from typing import Protocol

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.telemetry import TelemetryPort, WorkerTelemetry
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_ID_MISMATCH,
    REASON_UNREADABLE,
)
from ragcore.core.statistics_measures import (
    FACETS,
    STAGE_DISCOVERY,
    STAGE_PHASE1,
    STEP_READ,
    XML_BYTES,
    document_measure,
    milliseconds_since,
    step_measure,
)
from ragcore.core.telemetry_events import (
    DOCUMENT_FETCHED,
    DOCUMENT_ID_MISMATCH,
    DOCUMENT_UNREADABLE,
    DOCUMENT_VERSION_SKIPPED,
)
from ragcore.orchestration.kedro.stage_clock import StageClock

logger = logging.getLogger(__name__)

# Une raison absente d'ici lève `KeyError` plutôt que de finir dans un fourre-tout
_SKIP_EVENT_BY_REASON = {
    REASON_EXPORT_ARTIFACT: DOCUMENT_VERSION_SKIPPED,
    REASON_UNREADABLE: DOCUMENT_UNREADABLE,
    REASON_ID_MISMATCH: DOCUMENT_ID_MISMATCH,
}


class InventorySink(Protocol):
    """Le bilan du run, qui porte le nombre de documents retenus par source."""

    def record_inventories(
        self, inventories: Mapping[SourceName, SourceInventory]
    ) -> None: ...


def connect_node(
    connector: BaseConnector,
    pipeline_context: PipelineContext,
    telemetry: WorkerTelemetry,
    stage_clock: StageClock,
    run_sink: InventorySink,
    nuke_done: dict[str, bool],
) -> list[RawDocument]:
    del nuke_done  # simple signal : nukeAll tourne avant connect

    with stage_clock.stage(STAGE_DISCOVERY):
        inventories = connector.discover()
    run_sink.record_inventories(inventories)
    _announce(inventories)

    with stage_clock.stage(STAGE_PHASE1):
        documents = _read_all(connector, telemetry)

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


def _announce(inventories: Mapping[SourceName, SourceInventory]) -> None:
    for source, inventory in inventories.items():
        if inventory.retained < inventory.total:
            logger.warning(
                "Passe 1 : %s, %d documents retenus sur %d (ingestion_ratio)",
                source.value,
                inventory.retained,
                inventory.total,
            )
        else:
            logger.info("Passe 1 : %s, %d documents", source.value, inventory.total)


def _read_all(
    connector: BaseConnector, telemetry: WorkerTelemetry
) -> list[RawDocument]:
    """Le temps entre deux documents émis est celui de la lecture du second."""
    documents: list[RawDocument] = []
    started = perf_counter()
    for document in connector.fetch_all():
        _measure(telemetry, document, milliseconds_since(started))
        documents.append(document)
        started = perf_counter()
    return documents


def _measure(telemetry: WorkerTelemetry, document: RawDocument, read_ms: float) -> None:
    files = document.payload["files"]
    ref = document.source_document_id
    telemetry.record_measure(step_measure(document.source, STEP_READ), read_ms, ref)
    sizes = {
        XML_BYTES: sum(Path(file).stat().st_size for file in files),
        FACETS: len(files),
    }
    for name, size in sizes.items():
        telemetry.record_measure(document_measure(document.source, name), size, ref)


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
