"""L'ingestion d'un document, la phase 1.

Le document n'est écrit ici que comme nœud : ses arêtes attendent la phase 2, quand
tous les nœuds du run existent, sinon une arête vers une cible pas encore écrite
tomberait dans le vide sans erreur.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from ragcore.core.models import (
    Identifier,
    ParsedDocument,
    RunId,
    SearchContent,
    UnformattedRelation,
)
from ragcore.core.models.audit import build_event
from ragcore.core.ports.document_repository import DocumentRepository
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.pending_repository import PendingRelationRepository
from ragcore.core.ports.search_index_repository import SearchIndexRepository
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.ports.unformatted_repository import UnformattedRelationRepository
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED

from .run_context import PipelineContext
from .saga import SagaExecutor, SagaStep


@dataclass(frozen=True)
class IngestionStores:
    """Les dépôts du corpus. ``pending`` n'est écrit qu'en phase 2.

    Le hook en ouvre un jeu, et chaque worker de la phase 1 le sien.
    """

    documents: DocumentRepository
    graph: GraphRepository
    search_index: SearchIndexRepository
    pending: PendingRelationRepository
    unformatted: UnformattedRelationRepository


async def _nothing_to_compensate() -> None:
    """Le nœud Neo4j est le dernier step : rien ne peut échouer après lui, et son propre
    échec annule sa transaction."""


class IngestDocumentUseCase:
    def __init__(self, stores: IngestionStores, telemetry: TelemetryPort) -> None:
        self._document_repo = stores.documents
        self._graph_repo = stores.graph
        self._search_index = stores.search_index
        self._unformatted_repo = stores.unformatted
        self._telemetry = telemetry

    async def execute(
        self,
        parsed: ParsedDocument,
        content: SearchContent,
        context: PipelineContext,
        unformatted_relations: Sequence[UnformattedRelation] = (),
    ) -> None:
        unformatted_step = self._unformatted_step(
            parsed.identifier, unformatted_relations, context.run_id
        )
        steps = self._saga_steps(parsed, content, unformatted_step)
        await SagaExecutor(self._telemetry).execute(steps, context)
        self._emit_persisted(parsed, context)

    def _saga_steps(
        self,
        parsed: ParsedDocument,
        content: SearchContent,
        unformatted_step: SagaStep,
    ) -> list[SagaStep]:
        """Mongo → relations non formatées → OpenSearch → nœud Neo4j.

        Les compensations Mongo et OpenSearch suppriment : juste pour une première
        écriture, mais un document déjà en base est perdu au lieu d'être restauré. Ce cas n'existe qu'en
        run incrémental (jamais après `nuke_all`) et le run suivant le réécrit depuis la
        source.

        Neo4j en dernier : ses arêtes entrantes viennent d'autres documents, il est le
        moins compensable.
        """
        return [
            SagaStep(
                name="mongo_upsert",
                forward=lambda: self._document_repo.upsert(parsed),
                compensate=lambda: self._document_repo.delete(parsed.identifier),
            ),
            unformatted_step,
            SagaStep(
                name="opensearch_index",
                forward=lambda: self._search_index.index_document(parsed, content),
                compensate=lambda: self._search_index.delete_document(
                    parsed.identifier
                ),
            ),
            SagaStep(
                name="neo4j_merge_node",
                forward=lambda: self._graph_repo.merge_document_node(parsed),
                compensate=_nothing_to_compensate,
            ),
        ]

    def _unformatted_step(
        self,
        identifier: Identifier,
        unformatted_relations: Sequence[UnformattedRelation],
        run_id: RunId,
    ) -> SagaStep:
        """Elles s'accumulent de run en run : la compensation ne retire que celles nées
        dans ce run."""
        return SagaStep(
            name="mongo_unformatted_upsert",
            forward=lambda: self._unformatted_repo.upsert_many(
                unformatted_relations, run_id
            ),
            compensate=lambda: self._unformatted_repo.delete_first_seen(
                identifier, run_id
            ),
        )

    def _emit_persisted(self, parsed: ParsedDocument, context: PipelineContext) -> None:
        """Seulement après succès total de la saga."""
        self._telemetry.emit(
            build_event(
                event_type=DOCUMENT_PERSISTED,
                run_id=context.run_id,
                source=parsed.source,
                document_id=parsed.identifier.serialize(),
            )
        )
