"""Use case d'ingestion d'UN document — la phase 1, en trois steps (§11).

Les relations ne sont plus ici. Elles sortaient jadis dans cette même saga, ce qui
condamnait chaque arête à dépendre de l'ordre d'ingestion : ``upsert_relations``
fait ``MATCH (a) MATCH (b)``, et si la cible ``b`` n'était pas encore écrite,
l'arête tombait dans le vide — sans erreur, sans trace, sans rien.

Le document écrit ici n'est donc qu'un NŒUD. Ses arêtes sont écrites en phase 2,
après que tous les nœuds du run existent (ResolveRelationsService). Cette attente
n'est pas un ``join()`` caché dans du code applicatif : c'est une arête du DAG.
"""

from datetime import UTC, datetime

from ragcore.core.models import (
    EmbeddedChunk,
    ManifestEntry,
    Operation,
    OwnerId,
    ParsedDocument,
    SourceIdentifier,
)
from ragcore.core.models.audit import build_event
from ragcore.core.ports.document_repository import DocumentRepository
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.manifest_repository import ManifestRepository
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.ports.vector_repository import VectorRepository
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED

from .run_context import PipelineContext
from .saga import SagaExecutor, SagaStep

# Le nœud Neo4j existe, mais pas ses arêtes : le dire « neo4j » tout court serait
# affirmer une complétude que la phase 1 ne livre pas.
TARGETS_WRITTEN = ["mongo", "qdrant", "neo4j:node"]


class IngestDocumentUseCase:
    def __init__(
        self,
        document_repo: DocumentRepository,
        graph_repo: GraphRepository,
        vector_repo: VectorRepository,
        manifest_repo: ManifestRepository,
        telemetry: TelemetryPort,
    ) -> None:
        self._document_repo = document_repo
        self._graph_repo = graph_repo
        self._vector_repo = vector_repo
        self._manifest_repo = manifest_repo
        self._telemetry = telemetry

    async def execute(
        self,
        parsed: ParsedDocument,
        embedded_chunks: list[EmbeddedChunk],
        operation: Operation,
        context: PipelineContext,
    ) -> None:
        saga = SagaExecutor(self._telemetry)

        # Neo4j en dernier : c'est le store le moins librement compensable (ses arêtes
        # entrantes viennent d'autres documents). En position terminale, sa compensation
        # n'est appelée que si LUI échoue — mais elle existe désormais (§8) : conditionnelle
        # (DETACH DELETE si orphelin, dé-hydratation en `:Unknown` si cité), plus un `_noop`.
        steps = [
            SagaStep(
                name="mongo_upsert",
                forward=lambda: self._mongo_delete_then_insert(parsed, operation),
                compensate=lambda: self._document_repo.delete(
                    parsed.identifier, parsed.owner_id
                ),
            ),
            SagaStep(
                name="qdrant_upsert",
                forward=lambda: self._qdrant_delete_then_insert(
                    parsed.identifier, parsed.owner_id, embedded_chunks
                ),
                compensate=lambda: self._vector_repo.delete_by_document(
                    parsed.identifier, parsed.owner_id
                ),
            ),
            SagaStep(
                name="neo4j_merge_node",
                forward=lambda: self._graph_repo.merge_document_node(parsed),
                # §8 : le nœud n'est plus intouchable. S'il n'est cité par personne, on le
                # supprime ; s'il l'est, on le dé-hydrate en `:Unknown` sans arracher la
                # citation d'autrui. Fin du `_noop` — le nœud orphelin ne survit plus.
                compensate=lambda: self._graph_repo.compensate_document_node(
                    parsed.identifier, parsed.owner_id
                ),
            ),
        ]

        # La saga peut lever — le manifest n'est alors PAS écrit.
        await saga.execute(steps, context)

        # Manifest uniquement après succès total. Append-only : on ajoute, jamais
        # on ne met à jour.
        await self._manifest_repo.append(
            ManifestEntry(
                identifier=parsed.identifier,
                source=parsed.source,
                owner_id=parsed.owner_id,
                operation=operation,
                reason=None,
                targets_written=list(TARGETS_WRITTEN),
                processed_at=datetime.now(UTC),
            )
        )

        self._telemetry.emit(
            build_event(
                event_type=DOCUMENT_PERSISTED,
                run_id=context.run_id,
                owner_id=parsed.owner_id,
                source=parsed.source,
                document_id=parsed.identifier.serialize(),
                payload={"operation": operation.value},
            )
        )

    async def _mongo_delete_then_insert(
        self, parsed: ParsedDocument, operation: Operation
    ) -> None:
        if operation == Operation.UPDATE:
            await self._document_repo.delete(parsed.identifier, parsed.owner_id)
        await self._document_repo.upsert(parsed)

    async def _qdrant_delete_then_insert(
        self,
        identifier: SourceIdentifier,
        owner_id: OwnerId,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        await self._vector_repo.delete_by_document(identifier, owner_id)
        await self._vector_repo.upsert(embedded_chunks)
