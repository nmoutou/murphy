"""La composition de l'ingestion : embedder, briques de traitement, pool de la phase 1.

Tout ce qui s'assemble ici est soit pur (parser, chunker, extracteur), soit créé à
l'appel (l'embedder ouvre son client HTTP à chaque requête, les workers leurs clients
dans leur propre runtime) : rien n'est lié à la boucle du hook.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ragcore.adapters.config.settings import EmbeddingRuntimeSettings, InfraSettings
from ragcore.adapters.embedding.local_embedder import LocalEmbedder
from ragcore.adapters.embedding.noop_embedder import NoopEmbedder
from ragcore.adapters.embedding.openai_embedder import (
    OpenAIEmbedder,
    assert_service_serves_model,
)
from ragcore.adapters.runtime import AsyncioRuntimeFactory
from ragcore.adapters.storage.mongo.audit_repository import MongoAuditRepository
from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.telemetry.factory import WorkerTelemetryFactory
from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.ingestion_runner import IngestionRunner
from ragcore.application.run_context import PipelineContext
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.orchestration.kedro.run_plan import RunPlan
from ragcore.orchestration.kedro.stores import open_clients, open_document_stores
from ragcore.orchestration.kedro.workload import UseCaseFactory, build_document_workload
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
from ragcore.sources.registry import definition_for

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
# `chunk_size` (cf. la note de perf dans ETAT.md).
_WORKER_COUNT = 4


@runtime_checkable
class ReportsTruncations(Protocol):
    """Un embedder qui compte les chunks qu'il a dû raccourcir (``OpenAIEmbedder``).

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
    chunker: StructuralChunker
    extractor: RoutingRelationExtractor
    embedder: BaseEmbedder


def prepare_embedder(
    embedding_settings: EmbeddingRuntimeSettings,
    plan: RunPlan,
    runtime: AsyncRuntime,
) -> BaseEmbedder:
    """Vérifie les préconditions du fournisseur, puis construit son embedder.

    Le MODÈLE et la DIMENSION viennent du workflow (ils décident des vecteurs, donc ils
    sont hashés) ; le PROVIDER et son transport viennent de l'infra (ils ne changent
    aucun vecteur). La couture passe exactement ici.
    """
    embedding = plan.workflow.embedding
    match embedding_settings.provider:
        case "openai":
            _assert_service_serves_model(embedding_settings, plan, runtime)
            return OpenAIEmbedder(
                api_key=embedding_settings.api_key,
                model_name=embedding.model_name,
                dimension=embedding.dimension,
                batch_size=embedding_settings.batch_size,
                base_url=embedding_settings.service_url,
            )
        case "noop":
            _warn_null_vectors(plan.collection)
            return NoopEmbedder(dimension=embedding.dimension)
        case "local":
            return LocalEmbedder(
                model_name=embedding.model_name, dimension=embedding.dimension
            )


def _assert_service_serves_model(
    embedding_settings: EmbeddingRuntimeSettings, plan: RunPlan, runtime: AsyncRuntime
) -> None:
    """Le modèle qui vient de BAPTISER la collection est-il celui que le service SERT ?

    TEI ne sert qu'un modèle — celui de son `--model-id` — et ignore le champ `model` de
    la requête. Si le conteneur et `parameters.yml` divergent, on écrit les vecteurs d'un
    modèle dans la collection nommée d'après un autre : rien ne lève, rien ne loggue, et
    ça ne se voit qu'à la recherche.

    C'est une PRÉCONDITION du run, et c'est pourquoi elle est ici et pas dans
    l'embedder : `SagaExecutor` attrape `Exception` pour compenser, donc levée dans un
    worker elle deviendrait un échec par document — compensé N fois, avec un run qui
    conclut « ok ». Vérifier N fois quel modèle le service sert n'aurait de toute façon
    aucun sens : il n'en sert qu'un, et il le dit une fois pour toutes.
    """
    runtime.run(
        assert_service_serves_model(
            embedding_settings.service_url or "",
            plan.workflow.embedding.model_name,
        )
    )


def _warn_null_vectors(collection: str) -> None:
    """`provider` n'entre PAS dans l'empreinte (§6) : deux façons d'atteindre le même
    modèle produisent les mêmes vecteurs. Mais `noop` n'atteint aucun modèle — il produit
    des vecteurs NULS, et les écrit dans la collection du vrai modèle, où plus rien ne
    les distingue ensuite. La doctrine assume la verrue ; elle n'exige pas qu'elle soit
    muette.
    """
    logger.warning(
        "EMBEDDING_PROVIDER=noop : les vecteurs seront NULS et seront écrits dans "
        "la collection %s — celle du vrai modèle, où rien ne les distinguera. "
        "Hygiène de test uniquement : pour un vrai run, EMBEDDING_PROVIDER=openai.",
        collection,
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
        chunker=StructuralChunker(
            max_chunk_size=plan.workflow.chunking.size,
            overlap=plan.workflow.chunking.overlap,
        ),
        extractor=RoutingRelationExtractor(
            {
                source: GenericRelationExtractor(definition.table, source)
                for source, definition in definitions.items()
            }
        ),
        embedder=embedder,
    )


def build_runner(
    settings: InfraSettings,
    plan: RunPlan,
    context: PipelineContext,
    stack: ProcessingStack,
) -> IngestionRunner:
    """Assemble le pool de la phase 1 : deux fabriques + un use case PAR worker (§11).

    La collection des workers est celle du ``plan`` — la même que le ``vector_repo`` du
    hook : une seconde dérivation ferait écrire workers et phase 2 dans deux collections.
    """
    workload = build_document_workload(
        chunker=stack.chunker,
        embedder=stack.embedder,
        extractor=stack.extractor,
        use_case_factory=_use_case_factory(settings, plan),
        context=context,
        embedding_enabled=plan.embedding_enabled,
    )
    return IngestionRunner(
        workload=workload,
        runtime_factory=AsyncioRuntimeFactory(),
        telemetry_factory=_telemetry_factory(settings, context),
        worker_count=_WORKER_COUNT,
    )


def _use_case_factory(settings: InfraSettings, plan: RunPlan) -> UseCaseFactory:
    def use_case_factory(telemetry: WorkerTelemetry) -> IngestDocumentUseCase:
        """Un use case PAR worker, sur des dépôts NEUFS et sa propre télémétrie.

        Les clients sont ouverts ici, dans le runtime du worker : ceux du hook sont liés
        à la boucle du hook, et tous les workers échoueraient sauf un.
        """
        stores = open_document_stores(open_clients(settings), settings, plan)
        return IngestDocumentUseCase(stores, telemetry)

    return use_case_factory


def _telemetry_factory(
    settings: InfraSettings, context: PipelineContext
) -> WorkerTelemetryFactory:
    meta_db = settings.mongodb_meta_db_name
    return WorkerTelemetryFactory(
        run_id=context.run_id,
        owner_id=context.owner_id,
        source=context.source,
        started_at=context.started_at,
        events_dir=Path(settings.meta_jsonl_dir) / "events",
        audit_repo_factory=lambda runtime: MongoAuditRepository(
            create_mongo_client(settings.mongodb_uri), meta_db
        ),
    )
