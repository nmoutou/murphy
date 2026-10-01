"""La composition de l'ingestion : embedder, briques de traitement, pool de la phase 1.

Tout ce qui s'assemble ici est soit pur (parser, chunker, extracteur), soit créé à
l'usage (l'embedder ouvre un client HTTP par boucle, les workers leurs clients dans leur
propre runtime) : rien n'est lié à la boucle du hook.
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

# Le pool de la phase 1. Un jour un paramètre ; pour l'instant une constante nommée,
# et non un « 4 » nu perdu dans le constructeur du runner.
#
# **Ne pas l'augmenter en espérant un gain : c'est mesuré, ça n'en donne pas.** 99,9 % du
# temps d'un document part dans l'embedding (parse 0,9 ms, chunk 0,1 ms, embed 1364 ms),
# et le mur est le GPU lui-même, pas le nombre de requêtes qu'on lui envoie. Un banc
# d'essai isolé promettait ×4 en passant à 16 workers ; le run réel n'a rien gagné
# (751 s → 738 s). Le seul levier réel est de calculer MOINS de vecteurs, c.-à-d.
# `CHUNKING_MAX_CHARS` (cf. la note de perf dans ETAT.md).
_WORKER_COUNT = 4


@runtime_checkable
class ReportsTruncations(Protocol):
    """Un embedder qui compte les chunks qu'il a dû raccourcir (``TeiEmbedder``).

    Hors du port ``BaseEmbedder`` : c'est un détail d'UNE implémentation, que le hook lit
    une fois en fin de run pour le déclarer au bilan.
    """

    @property
    def truncations(self) -> int: ...


@dataclass(frozen=True)
class ProcessingStack:
    """Les briques de traitement du run, une par rôle — routées par source dessous."""

    connector: CompositeConnector
    parser: RoutingParser
    steps: WorkloadSteps
    """Ce que chaque worker applique à un document : chunker, embedder, extracteur."""


def prepare_embedder(
    embedding_settings: EmbeddingRuntimeSettings, runtime: AsyncRuntime
) -> TeiEmbedder:
    """Vérifie le modèle que sert TEI, mesure sa dimension, puis construit l'embedder.

    C'est une PRÉCONDITION du run, et c'est pourquoi elle est ici et pas dans
    l'embedder : `SagaExecutor` attrape `Exception` pour compenser, donc levée dans un
    worker elle deviendrait un échec par document — compensé N fois, avec un run qui
    conclut « ok ». Vérifier N fois quel modèle le service sert n'aurait de toute façon
    aucun sens : il n'en sert qu'un, et il le dit une fois pour toutes.
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
    """Les briques du run, une PAR source, et un routeur au-dessus de chacune.

    **Aucun nom de source ici.** Le parser, le chunker et l'extracteur sont génériques
    (§3) ; les connecteurs viennent du registre. Ce bloc est identique pour LEGI et pour
    les cinq juri — c'est très exactement la mesure du succès : ajouter une source n'a
    demandé aucune ligne dans l'assemblage.

    Chaque source a sa table de rôles (elles sont quatre distinctes) ; le routeur
    aiguille sur `document.source`. Les nœuds, eux, ne voient qu'un connecteur et qu'un
    parser : les routeurs respectent les mêmes ports, donc le DAG ignore qu'il y a six
    sources derrière.
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
    """Assemble le pool de la phase 1 : deux fabriques + un use case PAR worker (§11).

    La collection des workers est celle du ``plan`` — la même que le ``vector_repo`` du
    hook.
    """
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
        """Un use case PAR worker, sur des dépôts NEUFS et sa propre télémétrie.

        Les clients sont ouverts ici, dans le runtime du worker : ceux du hook sont liés
        à la boucle du hook, et tous les workers échoueraient sauf un.
        """
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
