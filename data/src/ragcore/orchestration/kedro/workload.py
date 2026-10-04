"""Le travail sur un document, tel que le pool le parallélise.

- Le workload tient la télémétrie du worker : il déclare les inconnus et les liens
  perdus que l'extracteur remonte dans sa valeur de retour. Les signaux de parse sont
  déclarés au site de parse.
- Il extrait les relations sans les écrire : elles remontent vers la phase 2. La saga
  n'écrit que le nœud et les relations non formatées, dont la cible n'est pas un nœud.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.ingestion_runner import DocumentWorkload, WorkloadResult
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.chunk import Chunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.search_content import IndexedPassage, SearchContent
from ragcore.core.models.unknown_tally import UnknownExample
from ragcore.core.ports.chunker import BaseChunker
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.relation_extractor import (
    BaseRelationExtractor,
    ExtractionResult,
)
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.telemetry_events import PAYLOAD_COUNT_KEY, RELATION_UNKNOWN

__all__ = ["UseCaseFactory", "WorkloadSteps", "build_document_workload"]

# Un use case par worker : ses dépôts sont liés à la boucle qui les a touchés en premier.
# Le runtime reçoit la fermeture de ses clients.
UseCaseFactory = Callable[[WorkerTelemetry, AsyncRuntime], IngestDocumentUseCase]


@dataclass(frozen=True)
class WorkloadSteps:
    """Partagés entre les workers sans risque : chunker et extracteur sont purs,
    l'embedder crée son client HTTP à l'appel, sur la bonne boucle.
    """

    chunker: BaseChunker
    embedder: BaseEmbedder
    extractor: BaseRelationExtractor


def build_document_workload(
    steps: WorkloadSteps,
    use_case_factory: UseCaseFactory,
    context: PipelineContext,
    embedding_enabled: bool = True,
) -> DocumentWorkload:
    """``runtime`` et ``telemetry`` sont ceux du worker courant, fournis par le runner à
    chaque appel.

    ``embedding_enabled=False`` (dev, ADR-012) saute l'embedding : les passages partent
    dans l'index sans vecteur. Le booléen arrive déjà arbitré par le plan.
    """
    use_cases = _UseCasePerWorker(use_case_factory)

    def workload(
        parsed: ParsedDocument,
        runtime: AsyncRuntime,
        telemetry: WorkerTelemetry,
    ) -> WorkloadResult:
        extraction = _extract(steps.extractor, parsed, telemetry, context)

        chunks = steps.chunker.chunk(parsed)
        content = (
            runtime.run(_embed(steps.embedder, parsed.title, chunks))
            if embedding_enabled
            else _without_vectors(chunks)
        )

        use_case = use_cases.for_worker(telemetry, runtime)
        runtime.run(
            use_case.execute(parsed, content, context, extraction.unformatted_relations)
        )

        return WorkloadResult(relations=extraction.relations)

    return workload


async def _embed(
    embedder: BaseEmbedder, title: str, chunks: list[Chunk]
) -> SearchContent:
    """Le titre seulement sans passage (ADR-029) : celui d'un article (« L52-8 ») ou
    d'une décision n'a pas de sens pour un embedding."""
    if chunks:
        embedded = await embedder.embed(chunks)
        return SearchContent(
            passages=tuple(
                IndexedPassage(chunk=chunk.chunk, embedding=chunk.embedding)
                for chunk in embedded
            )
        )
    if not title:
        return SearchContent()
    return SearchContent(title_embedding=await embedder.embed_text(title))


def _without_vectors(chunks: list[Chunk]) -> SearchContent:
    return SearchContent(
        passages=tuple(IndexedPassage(chunk=chunk) for chunk in chunks)
    )


class _UseCasePerWorker:
    """Mémorisé : la fabrique ouvre trois clients. La clé est la télémétrie, que le
    runner construit une par worker.
    """

    def __init__(self, factory: UseCaseFactory) -> None:
        self._factory = factory
        self._use_cases: dict[int, IngestDocumentUseCase] = {}

    def for_worker(
        self, telemetry: WorkerTelemetry, runtime: AsyncRuntime
    ) -> IngestDocumentUseCase:
        key = id(telemetry)
        use_case = self._use_cases.get(key)
        if use_case is None:
            use_case = self._factory(telemetry, runtime)
            self._use_cases[key] = use_case
        return use_case


def _extract(
    extractor: BaseRelationExtractor,
    parsed: ParsedDocument,
    telemetry: WorkerTelemetry,
    context: PipelineContext,
) -> ExtractionResult:
    """Extrait les liens, déclare les inconnus et compte les liens perdus. Le seul
    appelant d'``extract()`` hors tests."""
    extraction = extractor.extract(parsed)
    _declare_unknowns(telemetry, extraction.unknowns, parsed)
    if extraction.lost_links:
        telemetry.emit(
            build_event(
                event_type=RELATION_UNKNOWN,
                run_id=context.run_id,
                source=parsed.source,
                document_id=parsed.identifier.serialize(),
                payload={PAYLOAD_COUNT_KEY: extraction.lost_links},
            )
        )
    return extraction


def _declare_unknowns(
    telemetry: WorkerTelemetry,
    unknowns: dict[str, list[str]],
    parsed: ParsedDocument,
) -> None:
    """L'extracteur ne dit pas de quelle facette vient le lien : l'exemple donne le
    premier fichier du document."""
    example = UnknownExample(
        identifier=parsed.identifier.serialize(),
        source_file=parsed.source_files[0] if parsed.source_files else "",
    )
    for category, values in unknowns.items():
        for value in values:
            telemetry.record_unknown(category, value, example)
