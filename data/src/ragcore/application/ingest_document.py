"""Use case d'ingestion d'UN document — la phase 1, en trois steps (§11).

Les relations ne sont plus ici. Elles sortaient jadis dans cette même saga, ce qui
condamnait chaque arête à dépendre de l'ordre d'ingestion : ``upsert_relations``
fait ``MATCH (a) MATCH (b)``, et si la cible ``b`` n'était pas encore écrite,
l'arête tombait dans le vide — sans erreur, sans trace, sans rien.

Le document écrit ici n'est donc qu'un NŒUD. Ses arêtes sont écrites en phase 2,
après que tous les nœuds du run existent (ResolveRelationsService). Cette attente
n'est pas un ``join()`` caché dans du code applicatif : c'est une arête du DAG.
"""

from dataclasses import dataclass

from ragcore.core.models import EmbeddedChunk, Identifier, ParsedDocument
from ragcore.core.models.audit import build_event
from ragcore.core.ports.document_repository import DocumentRepository
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.ports.vector_repository import VectorRepository
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED

from .run_context import PipelineContext
from .saga import SagaExecutor, SagaStep


@dataclass(frozen=True)
class IngestionStores:
    """Les trois dépôts qu'écrit l'ingestion d'un document — typés par leurs ports.

    Le hook en ouvre un jeu (maintenance, phase 2) et chaque worker de la phase 1 le sien
    (§11) : ``orchestration/kedro/stores.open_document_stores`` les fabrique.
    """

    documents: DocumentRepository
    graph: GraphRepository
    vectors: VectorRepository


class IngestDocumentUseCase:
    def __init__(self, stores: IngestionStores, telemetry: TelemetryPort) -> None:
        self._document_repo = stores.documents
        self._graph_repo = stores.graph
        self._vector_repo = stores.vectors
        self._telemetry = telemetry

    async def execute(
        self,
        parsed: ParsedDocument,
        embedded_chunks: list[EmbeddedChunk],
        context: PipelineContext,
    ) -> None:
        # La saga peut lever — le document n'est alors PAS déclaré persisté.
        await SagaExecutor(self._telemetry).execute(
            self._saga_steps(parsed, embedded_chunks), context
        )
        self._emit_persisted(parsed, context)

    def _saga_steps(
        self, parsed: ParsedDocument, embedded_chunks: list[EmbeddedChunk]
    ) -> list[SagaStep]:
        """Mongo → Qdrant → nœud Neo4j, chacun avec sa compensation.

        Compensation Mongo et le « trou » de la réécriture — la vérité, écrite ici.
        Le forward Mongo (`document_repo.upsert`) remplace en place ATOMIQUEMENT
        (`replace_one upsert=True`) : il ne détruit plus rien de lui-même, donc il n'y a
        plus de fenêtre à vide créée par notre propre code. La compensation
        `document_repo.delete` est le rollback JUSTE d'une première écriture (rien avant
        → supprimer). Sur un document déjà en base, elle supprime au lieu de restaurer
        l'ancien — mais ce chemin n'est atteint que si un step ULTÉRIEUR (Qdrant, Neo4j)
        échoue, et il ne survient jamais après un `nuke_all` (bases vides). Ce résiduel
        n'existe donc que sur le run INCRÉMENTAL — un chemin v1 — et retombe sur
        l'at-least-once (§13) : le run suivant relit la source et réécrit le document.
        Le vrai rollback versionné (snapshoter l'ancien pour le réinsérer) est un choix EXPLICITE
        de v1 : il paie un store de versions et une compensation qui peut elle-même
        échouer, pour fermer un trou qu'aucun run v0 n'emprunte.

        Neo4j en dernier : c'est le store le moins librement compensable (ses arêtes
        entrantes viennent d'autres documents). En position terminale, sa compensation
        n'est appelée que si LUI échoue — mais elle existe désormais (§8) : conditionnelle
        (DETACH DELETE si orphelin, dé-hydratation en `:Pending` si cité), plus un `_noop`.
        """
        return [
            SagaStep(
                name="mongo_upsert",
                forward=lambda: self._document_repo.upsert(parsed),
                compensate=lambda: self._document_repo.delete(parsed.identifier),
            ),
            SagaStep(
                name="qdrant_upsert",
                forward=lambda: self._qdrant_delete_then_insert(
                    parsed.identifier, embedded_chunks
                ),
                compensate=lambda: self._vector_repo.delete_by_document(
                    parsed.identifier
                ),
            ),
            SagaStep(
                name="neo4j_merge_node",
                forward=lambda: self._graph_repo.merge_document_node(parsed),
                # §8 : le nœud n'est plus intouchable. S'il n'est cité par personne, on le
                # supprime ; s'il l'est, on le dé-hydrate en `:Pending` sans arracher la
                # citation d'autrui. Fin du `_noop` — le nœud orphelin ne survit plus.
                compensate=lambda: self._graph_repo.compensate_document_node(
                    parsed.identifier
                ),
            ),
        ]

    def _emit_persisted(self, parsed: ParsedDocument, context: PipelineContext) -> None:
        """Uniquement après succès total : un document à moitié écrit n'est pas compté
        persisté."""
        self._telemetry.emit(
            build_event(
                event_type=DOCUMENT_PERSISTED,
                run_id=context.run_id,
                source=parsed.source,
                document_id=parsed.identifier.serialize(),
            )
        )

    async def _qdrant_delete_then_insert(
        self,
        identifier: Identifier,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        """Supprimer TOUS les points de ce document, PUIS insérer ceux du neuf.

        **Le ``delete`` n'est PAS une scorie ici — ne pas le retirer.** Contrairement à
        Mongo (un document = un enregistrement, remplaçable atomiquement par ``replace_one``),
        un document tient dans Qdrant en N points, un par chunk. Sur une réécriture dont la
        nouvelle version a MOINS de chunks que l'ancienne, un simple ``upsert`` écrase les
        points communs mais laisse les surnuméraires de l'ancienne version orphelins dans
        l'index — du contenu périmé qui remonterait aux recherches. Le ``delete_by_document``
        les emporte d'abord. Qdrant n'offre pas de « remplace tous les points de ce document »
        atomique : ce delete-puis-insert est le modèle, pas un défaut à corriger.

        Il subsiste donc, sur ce store et sur ce seul chemin, une fenêtre intra-step où les
        vecteurs du document sont absents. Comme le résiduel de la saga (cf. la docstring de
        classe), elle ne concerne QUE le run incrémental (après un ``nuke_all`` la
        collection est vide, ``delete_by_document`` ne trouve rien) et retombe sur
        l'at-least-once : le run suivant ré-écrit le document. Aucune donnée d'autorité
        n'est perdue — la source XML reste la vérité.
        """
        await self._vector_repo.delete_by_document(identifier)
        await self._vector_repo.upsert(embedded_chunks)
