from ragcore.core.models import OwnerId, SourceIdentifier
from ragcore.core.models.audit import build_event
from ragcore.core.ports.document_repository import DocumentRepository
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.manifest_repository import ManifestRepository
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.ports.vector_repository import VectorRepository
from ragcore.core.telemetry_events import DOCUMENT_DELETED

from .run_context import PipelineContext
from .saga import SagaExecutor, SagaStep


class DeleteDocumentUseCase:
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
        identifier: SourceIdentifier,
        owner_id: OwnerId,
        context: PipelineContext,
    ) -> None:
        saga = SagaExecutor(self._telemetry)

        steps = [
            SagaStep(
                name="neo4j_delete_relations",
                forward=lambda: self._graph_repo.delete_relations_from(identifier, owner_id, context.source),
                compensate=lambda: _noop(),  # pas de compensation possible sur delete relations
            ),
            SagaStep(
                name="mongo_delete",
                forward=lambda: self._document_repo.delete(identifier, owner_id),
                compensate=lambda: _noop(),
            ),
            SagaStep(
                name="qdrant_delete",
                forward=lambda: self._vector_repo.delete_by_document(identifier, owner_id),
                compensate=lambda: _noop(),
            ),
        ]

        await saga.execute(steps, context)
        await self._manifest_repo.delete(identifier, owner_id)

        self._telemetry.emit(
            build_event(
                event_type=DOCUMENT_DELETED,
                run_id=context.run_id,
                owner_id=owner_id,
                document_id=identifier.serialize(),
            )
        )


async def _noop() -> None:
    pass
