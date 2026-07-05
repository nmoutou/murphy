"""Use case d'ingestion de document — orchestration saga multi-store."""

from datetime import datetime, timezone

from ragcore.core.models import (
    EmbeddedChunk,
    ManifestEntry,
    Operation,
    OwnerId,
    ParsedDocument,
    Relation,
    SourceIdentifier,
)
from ragcore.core.models.audit import build_event
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED, RELATION_UPSERTED
from ragcore.core.ports.document_repository import DocumentRepository
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.manifest_repository import ManifestRepository
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.ports.vector_repository import VectorRepository

from .pipeline_context import PipelineContext
from .saga import SagaExecutor, SagaStep


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
        relations: list[Relation],
        operation: Operation,
        context: PipelineContext,
    ) -> None:
        saga = SagaExecutor(self._telemetry)

        steps = [
            SagaStep(
                name="neo4j_merge_node",
                forward=lambda: self._graph_repo.merge_document_node(parsed),
                compensate=lambda: _noop(),  # le nœud Neo4j n'est JAMAIS supprimé
            ),
            SagaStep(
                name="neo4j_upsert_relations",
                forward=lambda: self._graph_repo.upsert_relations(relations),
                # Compensation : supprimer les relations seulement s'il y en avait à écrire
                compensate=lambda: self._graph_repo.delete_relations_from(
                    parsed.identifier, parsed.owner_id, parsed.source
                )
                if relations
                else _noop(),
            ),
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
        ]

        # La Saga peut lever une exception — le manifest n'est PAS écrit dans ce cas
        await saga.execute(steps, context)

        # Manifest UNIQUEMENT après succès total de la Saga
        # Mode append-only : toujours ajouter une entrée, jamais updater
        await self._manifest_repo.append(
            ManifestEntry(
                identifier=parsed.identifier,
                source=parsed.source,
                owner_id=parsed.owner_id,
                operation=operation,
                reason=None,
                targets_written=["mongo", "neo4j", "qdrant"],
                processed_at=datetime.now(timezone.utc),
            )
        )

        if relations:
            self._telemetry.emit(
                build_event(
                    event_type=RELATION_UPSERTED,
                    run_id=context.run_id,
                    owner_id=parsed.owner_id,
                    source=parsed.source,
                    document_id=parsed.identifier.serialize(),
                    payload={"count": len(relations)},
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


async def _noop() -> None:
    pass
