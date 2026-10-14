"""Lit la source : la passe 1 de chaque connecteur, puis la passe 2 en flux, document par
document, et les compteurs de fin de flux."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from pathlib import Path
from time import perf_counter
from typing import Protocol

from ragcore.core.models.audit import build_event
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_ID_MISMATCH,
    REASON_UNREADABLE,
)
from ragcore.core.statistics_measures import (
    FACETS,
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

from .run_context import PipelineContext

__all__ = ["InventorySink", "SourceReading"]

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


class SourceReading:
    """``discover``, puis ``documents``, puis ``declare_counts`` : les compteurs ne
    sont connus qu'en fin de flux."""

    def __init__(
        self,
        connector: BaseConnector,
        context: PipelineContext,
        telemetry: WorkerTelemetry,
    ) -> None:
        self._connector = connector
        self._context = context
        self._telemetry = telemetry
        self._fetched = 0

    def discover(self, sink: InventorySink) -> int:
        """Rend le nombre de documents retenus, toutes sources confondues."""
        inventories = self._connector.discover()
        sink.record_inventories(inventories)
        _announce(inventories)
        return sum(inventory.retained for inventory in inventories.values())

    def documents(self) -> Iterator[RawDocument]:
        """Le temps entre deux documents émis est celui de la lecture du second."""
        started = perf_counter()
        for document in self._connector.fetch_all():
            self._fetched += 1
            self._measure(document, milliseconds_since(started))
            yield document
            started = perf_counter()

    def declare_counts(self) -> None:
        """``document.fetched`` est le dénominateur de l'équation de complétude ; les
        écartés en sont hors, un compteur par raison."""
        self._emit(DOCUMENT_FETCHED, self._fetched)
        for reason, count in self._connector.skipped.items():
            self._emit(_SKIP_EVENT_BY_REASON[reason], count)

    def _measure(self, document: RawDocument, read_ms: float) -> None:
        files = document.payload["files"]
        ref = document.source_document_id
        source = document.source
        self._telemetry.record_measure(step_measure(source, STEP_READ), read_ms, ref)
        sizes = {
            XML_BYTES: sum(Path(file).stat().st_size for file in files),
            FACETS: len(files),
        }
        for name, size in sizes.items():
            self._telemetry.record_measure(document_measure(source, name), size, ref)

    def _emit(self, event_type: str, count: int) -> None:
        self._telemetry.emit(
            build_event(
                event_type=event_type,
                run_id=self._context.run_id,
                source=self._context.source,
                payload={"count": count},
            )
        )


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
