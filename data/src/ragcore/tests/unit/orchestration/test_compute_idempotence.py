"""Le node `compute_idempotence` ne range en `parse_error` que ce que le port promet.

Le contrat de ``BaseParser`` : ``ValidationError`` si le document est irrecevable,
``ParseError`` s'il est illisible. Le node rattrapait tout ``Exception`` comme une
« autre erreur de parsing » : un bug du run (un document qu'aucun parser ne sait
router) devenait un rejet PAR DOCUMENT, compté et exclu en silence. Il remonte
désormais, et arrête le run.
"""

from datetime import UTC, datetime

import pytest

from ragcore.application.run_context import PipelineContext
from ragcore.core.exceptions import ParseError
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import Operation, SourceName
from ragcore.core.ports.parser import ParseResult
from ragcore.core.services.exclusion_reasons import REASON_PARSE_ERROR
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED
from ragcore.orchestration.kedro.nodes.compute_idempotence import (
    compute_idempotence_node,
)
from ragcore.tests.fakes.repositories import InMemoryManifestRepository
from ragcore.tests.fakes.runtime import FakeRuntime
from ragcore.tests.fakes.telemetry import RecordingTelemetry


class _FailingParser:
    """Parser idiot : lève l'exception qu'on lui donne, pour chaque document."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def parse(self, raw: RawDocument) -> ParseResult:
        del raw
        raise self._error


def _raw_document() -> RawDocument:
    return RawDocument(
        source=SourceName.LEGI,
        source_document_id="doc-1",
        payload={},
        fetched_at=datetime.now(UTC),
    )


def _run(
    parser: _FailingParser,
    manifest: InMemoryManifestRepository,
    telemetry: RecordingTelemetry,
) -> list[str]:
    runtime = FakeRuntime(worker_id=0)
    try:
        _, to_skip = compute_idempotence_node(
            raw_documents=[_raw_document()],
            parser=parser,
            manifest_repo=manifest,
            pipeline_context=PipelineContext.create(),
            telemetry=telemetry,
            pipeline_runtime=runtime,
            exportation_params={},
        )
    finally:
        runtime.close()
    return to_skip


def test_une_ParseError_exclut_le_document_et_le_compte() -> None:
    manifest = InMemoryManifestRepository()
    telemetry = RecordingTelemetry()

    to_skip = _run(_FailingParser(ParseError("XML malformé")), manifest, telemetry)

    assert to_skip == ["doc-1"]
    assert [e.operation for e in manifest.entries] == [Operation.EXCLUDED]
    invalidated = telemetry.events_of(DOCUMENT_INVALIDATED)
    assert [e.payload["reason"] for e in invalidated] == [REASON_PARSE_ERROR]


def test_une_exception_HORS_contrat_arrete_le_run() -> None:
    """Le cas réel : ``RoutingParser`` lève ``ValueError`` pour un document qu'aucun
    parser ne sait router. Ce n'est pas un document illisible, c'est un bug du run."""
    manifest = InMemoryManifestRepository()
    telemetry = RecordingTelemetry()

    with pytest.raises(ValueError, match="Aucun parser"):
        _run(
            _FailingParser(ValueError("Aucun parser pour 'cass'")), manifest, telemetry
        )

    assert manifest.entries == [], "le document n'est pas exclu en silence"
    assert telemetry.events_of(DOCUMENT_INVALIDATED) == []
