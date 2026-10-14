"""L'ingestion d'un document, la phase 1.

Le document n'est écrit ici que comme nœud : ses arêtes attendent la phase 2 dans
``transit_relations``, quand tous les nœuds du run existent, sinon une arête vers une
cible pas encore écrite tomberait dans le vide sans erreur.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from ragcore.core.models import (
    Identifier,
    ParsedDocument,
    Relation,
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
from ragcore.core.ports.transit_repository import TransitRelationRepository
from ragcore.core.ports.unformatted_repository import UnformattedRelationRepository
from ragcore.core.statistics_measures import STEP_MONGO, STEP_NEO4J, STEP_OPENSEARCH
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED

from .run_context import PipelineContext
from .saga import SagaExecutor, SagaStep

_MONGO_UPSERT = "mongo_upsert"
_MONGO_UNFORMATTED_UPSERT = "mongo_unformatted_upsert"
_MONGO_TRANSIT_INSERT = "mongo_transit_insert"
_OPENSEARCH_INDEX = "opensearch_index"
_NEO4J_MERGE_NODE = "neo4j_merge_node"

_STEP_MEASURES = {
    _MONGO_UPSERT: STEP_MONGO,
    _MONGO_UNFORMATTED_UPSERT: STEP_MONGO,
    _MONGO_TRANSIT_INSERT: STEP_MONGO,
    _OPENSEARCH_INDEX: STEP_OPENSEARCH,
    _NEO4J_MERGE_NODE: STEP_NEO4J,
}
"""Une base, une mesure : les étapes Mongo s'additionnent."""


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
    transit: TransitRelationRepository


@dataclass(frozen=True)
class DocumentRelations:
    """Ce que l'extraction a tiré d'un document."""

    relations: Sequence[Relation] = field(default_factory=tuple)
    """Vers une cible identifiée : en transit jusqu'à la phase 2."""
    unformatted: Sequence[UnformattedRelation] = field(default_factory=tuple)
    """Vers une cible décrite, sans nœud (ADR-021)."""


async def _nothing_to_compensate() -> None:
    """Le nœud Neo4j est le dernier step : rien ne peut échouer après lui, et son propre
    échec annule sa transaction."""


class IngestDocumentUseCase:
    def __init__(self, stores: IngestionStores, telemetry: TelemetryPort) -> None:
        self._document_repo = stores.documents
        self._graph_repo = stores.graph
        self._search_index = stores.search_index
        self._unformatted_repo = stores.unformatted
        self._transit_repo = stores.transit
        self._telemetry = telemetry

    async def execute(
        self,
        parsed: ParsedDocument,
        content: SearchContent,
        context: PipelineContext,
        relations: DocumentRelations = DocumentRelations(),
    ) -> dict[str, float]:
        """Rend la durée d'écriture dans chaque base, en millisecondes."""
        relation_steps = self._relation_steps(
            parsed.identifier, relations, context.run_id
        )
        steps = self._saga_steps(parsed, content, relation_steps)
        durations = await SagaExecutor(self._telemetry).execute(steps, context)
        self._emit_persisted(parsed, context)
        return _by_store(durations)

    def _saga_steps(
        self,
        parsed: ParsedDocument,
        content: SearchContent,
        relation_steps: list[SagaStep],
    ) -> list[SagaStep]:
        """Mongo → relations non formatées → relations en transit → OpenSearch → nœud
        Neo4j.

        Les compensations Mongo et OpenSearch suppriment : juste pour une première
        écriture, mais un document déjà en base est perdu au lieu d'être restauré. Ce cas n'existe qu'en
        run incrémental (jamais après `nuke_all`) et le run suivant le réécrit depuis la
        source.

        Neo4j en dernier : ses arêtes entrantes viennent d'autres documents, il est le
        moins compensable.
        """
        return [
            SagaStep(
                name=_MONGO_UPSERT,
                forward=lambda: self._document_repo.upsert(parsed),
                compensate=lambda: self._document_repo.delete(parsed.identifier),
            ),
            *relation_steps,
            SagaStep(
                name=_OPENSEARCH_INDEX,
                forward=lambda: self._search_index.index_document(parsed, content),
                compensate=lambda: self._search_index.delete_document(
                    parsed.identifier
                ),
            ),
            SagaStep(
                name=_NEO4J_MERGE_NODE,
                forward=lambda: self._graph_repo.merge_document_node(parsed),
                compensate=_nothing_to_compensate,
            ),
        ]

    def _relation_steps(
        self,
        identifier: Identifier,
        relations: DocumentRelations,
        run_id: RunId,
    ) -> list[SagaStep]:
        """Les non formatées s'accumulent de run en run : la compensation ne retire que
        celles nées dans ce run. Les relations en transit ne vivent que le temps du
        run : la compensation retire celles du document pour ce run (ADR-034 §4)."""
        return [
            SagaStep(
                name=_MONGO_UNFORMATTED_UPSERT,
                forward=lambda: self._unformatted_repo.upsert_many(
                    relations.unformatted, run_id
                ),
                compensate=lambda: self._unformatted_repo.delete_first_seen(
                    identifier, run_id
                ),
            ),
            SagaStep(
                name=_MONGO_TRANSIT_INSERT,
                forward=lambda: self._transit_repo.insert_many(
                    relations.relations, run_id
                ),
                compensate=lambda: self._transit_repo.delete_for_source(
                    identifier, run_id
                ),
            ),
        ]

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


def _by_store(durations: dict[str, float]) -> dict[str, float]:
    by_store: dict[str, float] = {}
    for step, milliseconds in durations.items():
        store = _STEP_MEASURES[step]
        by_store[store] = by_store.get(store, 0.0) + milliseconds
    return by_store
