"""La composition de l'ingestion : embedder, briques de traitement, pool de la phase 1.

Rien ici n'est lié à la boucle du hook : tout est pur, ou crée ses clients à l'usage.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ragcore.adapters.config.settings import EmbeddingRuntimeSettings, InfraSettings
from ragcore.adapters.embedding.served_model import inspect_served_model
from ragcore.adapters.embedding.tei_embedder import EmbeddingTransport, TeiEmbedder
from ragcore.adapters.runtime import AsyncioRuntimeFactory
from ragcore.adapters.telemetry.factory import WorkerTelemetryFactory
from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.ingestion_runner import IngestionRunner
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.enums import SourceName
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.orchestration.kedro.run_plan import RunPlan
from ragcore.orchestration.kedro.stores import open_clients, open_document_stores
from ragcore.orchestration.kedro.workload import (
    UseCaseFactory,
    WorkloadSteps,
    build_document_workload,
)
from ragcore.sources.composite import (
    CompositeConnector,
    RoutingParser,
    RoutingRelationExtractor,
)
from ragcore.sources.generic import (
    GenericParser,
    GenericRelationExtractor,
    StructuralChunker,
)
from ragcore.sources.registry import SourceDefinition, definition_for

__all__ = [
    "ProcessingStack",
    "ReportsTruncations",
    "build_processing_stack",
    "build_runner",
    "prepare_embedder",
]

logger = logging.getLogger(__name__)

# L'augmenter ne gagne rien (mesuré : 16 workers, 751 s → 738 s) : 99,9 % du temps part
# dans l'embedding, et le mur est le GPU. Le seul levier est `CHUNKING_MAX_CHARS`.
_WORKER_COUNT = 4


@runtime_checkable
class ReportsTruncations(Protocol):
    """Un embedder qui compte les chunks qu'il a dû raccourcir : un détail de
    ``TeiEmbedder``, hors du port ``BaseEmbedder``."""

    @property
    def truncations(self) -> int: ...


@dataclass(frozen=True)
class ProcessingStack:
    """Une brique par rôle, routée par source dessous."""

    connector: CompositeConnector
    parser: RoutingParser
    steps: WorkloadSteps
    """Ce que chaque worker applique à un document."""


def prepare_embedder(
    embedding_settings: EmbeddingRuntimeSettings, runtime: AsyncRuntime
) -> TeiEmbedder:
    """Vérifie le modèle que sert TEI et mesure sa dimension : une précondition du run,
    vérifiée ici et non dans un worker (cf. ``EmbeddingModelMismatchError``).
    """
    model = runtime.run(
        inspect_served_model(embedding_settings.service_url, embedding_settings.model)
    )
    logger.info(
        "Modèle d'embedding : %s (%d dimensions)", model.model_name, model.dimension
    )
    return TeiEmbedder(
        model,
        EmbeddingTransport(
            base_url=embedding_settings.service_url,
            timeout_ms=embedding_settings.ingestion_timeout,
            batch_size=embedding_settings.batch_size,
        ),
    )


def build_processing_stack(
    plan: RunPlan, xml_root: Path, embedder: BaseEmbedder
) -> ProcessingStack:
    """Les briques du run, une par source, sous un routeur qui aiguille sur
    `document.source`. Aucun nom de source ici : ajouter une source ne touche pas
    l'assemblage.
    """
    definitions = {source: definition_for(source) for source in plan.sources}
    return ProcessingStack(
        connector=CompositeConnector(
            {
                source: definition.connector(xml_root / definition.subdirectory)
                for source, definition in definitions.items()
            }
        ),
        parser=RoutingParser(
            {
                source: GenericParser(definition.table, source)
                for source, definition in definitions.items()
            }
        ),
        steps=_workload_steps(plan, definitions, embedder),
    )


def _workload_steps(
    plan: RunPlan,
    definitions: Mapping[SourceName, SourceDefinition],
    embedder: BaseEmbedder,
) -> WorkloadSteps:
    return WorkloadSteps(
        chunker=StructuralChunker(plan.chunking),
        embedder=embedder,
        extractor=RoutingRelationExtractor(
            {
                source: GenericRelationExtractor(
                    definition.table,
                    source,
                    skip_unconfigured=plan.skip_unconfigured,
                )
                for source, definition in definitions.items()
            }
        ),
    )


def build_runner(
    settings: InfraSettings,
    plan: RunPlan,
    context: PipelineContext,
    stack: ProcessingStack,
) -> IngestionRunner:
    """Le pool de la phase 1 : deux fabriques et un use case par worker."""
    workload = build_document_workload(
        steps=stack.steps,
        use_case_factory=_use_case_factory(
            settings, plan, stack.steps.embedder.dimension
        ),
        context=context,
        embedding_enabled=plan.embedding_enabled,
    )
    return IngestionRunner(
        workload=workload,
        runtime_factory=AsyncioRuntimeFactory(),
        telemetry_factory=_telemetry_factory(context),
        worker_count=_WORKER_COUNT,
    )


def _use_case_factory(
    settings: InfraSettings, plan: RunPlan, vector_size: int
) -> UseCaseFactory:
    def use_case_factory(telemetry: WorkerTelemetry) -> IngestDocumentUseCase:
        """Ouvre ses clients dans le runtime du worker : ceux du hook sont liés à la
        boucle du hook."""
        stores = open_document_stores(
            open_clients(settings), settings, plan, vector_size
        )
        return IngestDocumentUseCase(stores, telemetry)

    return use_case_factory


def _telemetry_factory(context: PipelineContext) -> WorkerTelemetryFactory:
    return WorkerTelemetryFactory(
        run_id=context.run_id,
        sources=context.sources,
        started_at=context.started_at,
    )
