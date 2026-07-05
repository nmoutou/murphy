from __future__ import annotations

from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.pipeline_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.telemetry_events import DOCUMENT_CHUNKED, DOCUMENT_EMBEDDED
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import Operation
from ragcore.core.ports.chunker import BaseChunker
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.relation_extractor import BaseRelationExtractor
from ragcore.core.ports.telemetry import TelemetryPort

from ._async_utils import run_async


def persist_node(
    to_process: list[tuple[ParsedDocument, Operation]],
    chunker: BaseChunker,
    embedder: BaseEmbedder,
    relation_extractor: BaseRelationExtractor,
    ingest_use_case: IngestDocumentUseCase,
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
) -> list[dict]:
    """For each document: chunk → embed → extract relations → persist via use case."""
    results: list[dict] = []
    run_id = pipeline_context.run_id
    owner_id = pipeline_context.owner_id

    for parsed, operation in to_process:
        chunks = chunker.chunk(parsed)
        telemetry.emit(
            build_event(
                event_type=DOCUMENT_CHUNKED,
                run_id=run_id,
                owner_id=owner_id,
                source=parsed.source,
                document_id=parsed.identifier.serialize(),
                payload={"count": len(chunks)},
            )
        )

        embedded = run_async(embedder.embed(chunks))
        telemetry.emit(
            build_event(
                event_type=DOCUMENT_EMBEDDED,
                run_id=run_id,
                owner_id=owner_id,
                source=parsed.source,
                document_id=parsed.identifier.serialize(),
                payload={"count": len(embedded)},
            )
        )

        relations = relation_extractor.extract(parsed)
        run_async(
            ingest_use_case.execute(parsed, embedded, relations, operation, pipeline_context)
        )
        results.append({
            "document_id": parsed.identifier.serialize(),
            "operation": operation.value,
        })
    return results
