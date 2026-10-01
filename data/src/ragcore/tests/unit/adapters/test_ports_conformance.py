"""Chaque adaptateur satisfait-il le port qu'il prétend implémenter ?

Le typage est **structurel** : aucun adaptateur n'hérite de son port. Rien, dans le
code, ne relie ``Neo4jGraphRepository`` à ``GraphRepository`` — sinon la promesse
qu'ils ont la même forme. ``isinstance`` contre un ``@runtime_checkable Protocol``
est la seule façon d'EXÉCUTER cette promesse.

Ce fichier n'est pas une formalité. C'est lui qui attrape :

- ``Neo4jGraphRepository`` qui ne s'importait pas (``RelationWriteResult`` manquant) ;
- ``RegistryAwareTelemetry`` qui n'exposait ni ``snapshot`` ni ``close``, et n'était
  donc PAS consommable par le pool — alors qu'elle est la pile que le pool consomme.

Ce qu'il ne prouve pas, et qu'il ne peut pas prouver : que le Cypher, le filtre
Qdrant ou l'``$setOnInsert`` font ce qu'on croit. Cela, seules les vraies bases le
disent — voir ``tests/integration/``.
"""

from datetime import UTC, datetime

from ragcore.adapters.embedding import EmbeddingTransport, TeiEmbedder
from ragcore.adapters.runtime import AsyncioRuntime, AsyncioRuntimeFactory
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.pending_repository import (
    MongoPendingRelationRepository,
)
from ragcore.adapters.storage.mongo.run_summary_repository import (
    MongoRunSummaryRepository,
)
from ragcore.adapters.storage.neo4j.graph_repository import (
    Neo4jGraphRepository,
    NodeLabels,
)
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.adapters.telemetry import (
    ConsoleLogTelemetry,
    NoopTelemetry,
    RunStatsAggregator,
    WorkerTelemetryFactory,
)
from ragcore.core.models.enums import SourceName
from ragcore.core.models.processing import EmbeddingModel
from ragcore.core.ports.document_repository import DocumentRepository
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.graph_repository import GraphRepository
from ragcore.core.ports.pending_repository import PendingRelationRepository
from ragcore.core.ports.run_summary_repository import RunSummaryRepository
from ragcore.core.ports.runtime import AsyncRuntime, AsyncRuntimeFactory
from ragcore.core.ports.telemetry import (
    TelemetryFactory,
    TelemetryPort,
    WorkerTelemetry,
)
from ragcore.core.ports.vector_repository import VectorRepository

RUN_ID = "abc123"


def _telemetry_factory() -> WorkerTelemetryFactory:
    return WorkerTelemetryFactory(
        run_id=RUN_ID,
        sources=(SourceName.LEGI,),
        started_at=datetime.now(UTC),
    )


class TestStorageAdapters:
    """Les clients sont ``None`` : construire l'objet n'ouvre aucune connexion, et
    la conformité est une propriété de la CLASSE, pas de la base derrière.
    """

    def test_mongo_document_repository(self) -> None:
        repo = MongoDocumentRepository.__new__(MongoDocumentRepository)
        assert isinstance(repo, DocumentRepository)

    def test_mongo_run_summary_repository(self) -> None:
        repo = MongoRunSummaryRepository.__new__(MongoRunSummaryRepository)
        assert isinstance(repo, RunSummaryRepository)

    def test_mongo_pending_repository(self) -> None:
        """Le dépôt du §13 : sans lui, une arête différée redevient un silence."""
        repo = MongoPendingRelationRepository.__new__(MongoPendingRelationRepository)
        assert isinstance(repo, PendingRelationRepository)

    def test_neo4j_graph_repository(self) -> None:
        """Le test qui a attrapé le ``NameError`` : le module ne s'importait pas,
        et son ``upsert_relations`` annonçait un ``RelationWriteResult`` inconnu.
        """
        repo = Neo4jGraphRepository(driver=None, labels=NodeLabels(by_prefix={}))
        assert isinstance(repo, GraphRepository)

    def test_qdrant_vector_repository(self) -> None:
        repo = QdrantVectorRepository.__new__(QdrantVectorRepository)
        assert isinstance(repo, VectorRepository)


class TestEmbedders:
    """Le seul embedder : TEI."""

    def test_tei_embedder(self) -> None:
        # La construire n'ouvre aucune connexion : la conformité reste hors-réseau.
        assert isinstance(
            TeiEmbedder(
                EmbeddingModel(model_name="whatever", dimension=768),
                EmbeddingTransport(base_url="http://tei.invalid/v1", timeout_ms=1),
            ),
            BaseEmbedder,
        )


class TestRuntime:
    """Le port qui condamne la globale ``_LOOP``."""

    def test_the_runtime_and_its_factory(self) -> None:
        factory = AsyncioRuntimeFactory()
        assert isinstance(factory, AsyncRuntimeFactory)

        runtime = factory.build(0)
        try:
            assert isinstance(runtime, AsyncRuntime)
        finally:
            runtime.close()

    def test_each_worker_gets_its_own_loop(self) -> None:
        """L'invariant 1, à la racine : deux workers ne partagent PAS de boucle.

        Une boucle partagée redeviendrait le point de sérialisation que §11 supprime
        — et les clients Motor posés dessus seraient inutilisables ailleurs.
        """
        factory = AsyncioRuntimeFactory()
        first, second = factory.build(0), factory.build(1)
        try:
            assert first is not second
            assert first._loop is not second._loop  # noqa: SLF001
        finally:
            first.close()
            second.close()

    def test_close_is_idempotent(self) -> None:
        """Le pool ferme sa pile en ``finally`` : une double fermeture ne doit pas
        transformer un échec d'ingestion en un second échec, plus bruyant.
        """
        runtime = AsyncioRuntime()
        runtime.close()
        runtime.close()

    def test_the_runtime_runs_a_coroutine(self) -> None:
        runtime = AsyncioRuntime()
        try:

            async def answer() -> int:
                return 42

            assert runtime.run(answer()) == 42
        finally:
            runtime.close()


class TestTelemetry:
    def test_the_backends_are_telemetry_ports(self) -> None:
        assert isinstance(NoopTelemetry(), TelemetryPort)
        assert isinstance(ConsoleLogTelemetry(), TelemetryPort)

    def test_the_aggregator_is_a_worker_telemetry(self) -> None:
        aggregator = RunStatsAggregator(
            run_id=RUN_ID,
            sources=(SourceName.LEGI,),
            started_at=datetime.now(UTC),
        )
        assert isinstance(aggregator, WorkerTelemetry)

    def test_the_factory_and_the_stack_it_builds(self) -> None:
        """Le test qui a attrapé la pile incomplète.

        ``RegistryAwareTelemetry`` n'exposait que ``emit`` et ``log`` : elle n'était
        donc PAS un ``WorkerTelemetry``, et le pool n'aurait pas pu la consommer —
        alors que c'est précisément la pile qu'il consomme.
        """
        factory = _telemetry_factory()
        assert isinstance(factory, TelemetryFactory)

        runtime = AsyncioRuntimeFactory().build(0)
        try:
            stack = factory.build(0, runtime)
            assert isinstance(stack, WorkerTelemetry)
        finally:
            runtime.close()

    def test_each_worker_gets_its_own_stack(self) -> None:
        """L'invariant 1 pour la télémétrie : rien de partagé, donc rien à verrouiller."""
        factory = _telemetry_factory()
        runtime_factory = AsyncioRuntimeFactory()
        r0, r1 = runtime_factory.build(0), runtime_factory.build(1)

        try:
            first, second = factory.build(0, r0), factory.build(1, r1)

            assert first is not second
            # Des agrégats distincts : la réduction du monoïde n'aurait aucun sens
            # si les workers écrivaient dans le même.
            assert (
                first._backends.aggregate  # noqa: SLF001
                is not second._backends.aggregate  # noqa: SLF001
            )
        finally:
            r0.close()
            r1.close()

    def test_an_unknown_reaches_the_aggregate(self) -> None:
        """Un vocabulaire non reconnu se DÉCLARE. Le fan-out doit le router vers
        l'agrégat, sinon le run tairait ce qu'il n'a pas compris.
        """
        runtime = AsyncioRuntimeFactory().build(0)
        try:
            stack = _telemetry_factory().build(0, runtime)
            stack.record_unknown("balise", "TRUC_INCONNU")

            assert stack.snapshot().unknowns == {"balise": ["TRUC_INCONNU"]}
        finally:
            runtime.close()
