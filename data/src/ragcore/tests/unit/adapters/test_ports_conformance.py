"""Chaque adaptateur satisfait-il son port ? Le typage est structurel : aucun adaptateur
n'hérite de son port, et ``isinstance`` contre un ``@runtime_checkable Protocol`` est la
seule façon de vérifier la promesse.

Ce que ces tests ne prouvent pas (Cypher, filtres Qdrant, ``$setOnInsert``), seules les
vraies bases le disent : ``tests/integration/``.
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
from ragcore.adapters.storage.mongo.unformatted_repository import (
    MongoUnformattedRelationRepository,
)
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.adapters.telemetry import (
    ConsoleLogTelemetry,
    NoopTelemetry,
    RunStatsAggregator,
    WorkerTelemetryFactory,
)
from ragcore.core.models.collision_tally import CollisionTally
from ragcore.core.models.enums import SourceName
from ragcore.core.models.processing import EmbeddingModel
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally
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
from ragcore.core.ports.unformatted_repository import UnformattedRelationRepository
from ragcore.core.ports.vector_repository import VectorRepository

RUN_ID = "abc123"


def _telemetry_factory() -> WorkerTelemetryFactory:
    return WorkerTelemetryFactory(
        run_id=RUN_ID,
        sources=(SourceName.LEGI,),
        started_at=datetime.now(UTC),
    )


class TestStorageAdapters:
    """Clients à ``None`` : la conformité est une propriété de la classe."""

    def test_mongo_document_repository(self) -> None:
        repo = MongoDocumentRepository.__new__(MongoDocumentRepository)
        assert isinstance(repo, DocumentRepository)

    def test_mongo_run_summary_repository(self) -> None:
        repo = MongoRunSummaryRepository.__new__(MongoRunSummaryRepository)
        assert isinstance(repo, RunSummaryRepository)

    def test_mongo_pending_repository(self) -> None:
        """Sans lui, une arête différée serait perdue."""
        repo = MongoPendingRelationRepository.__new__(MongoPendingRelationRepository)
        assert isinstance(repo, PendingRelationRepository)

    def test_mongo_unformatted_repository(self) -> None:
        """Sans lui, une cible décrite serait perdue (ADR-021)."""
        repo = MongoUnformattedRelationRepository.__new__(
            MongoUnformattedRelationRepository
        )
        assert isinstance(repo, UnformattedRelationRepository)

    def test_neo4j_graph_repository(self) -> None:
        """Le module doit s'importer, ``RelationWriteResult`` compris."""
        repo = Neo4jGraphRepository(driver=None)
        assert isinstance(repo, GraphRepository)

    def test_qdrant_vector_repository(self) -> None:
        repo = QdrantVectorRepository.__new__(QdrantVectorRepository)
        assert isinstance(repo, VectorRepository)


class TestEmbedders:
    """Le seul embedder : TEI."""

    def test_tei_embedder(self) -> None:
        # La construire n'ouvre aucune connexion
        assert isinstance(
            TeiEmbedder(
                EmbeddingModel(model_name="whatever", dimension=768),
                EmbeddingTransport(base_url="http://tei.invalid/v1", timeout_ms=1),
            ),
            BaseEmbedder,
        )


class TestRuntime:
    """Une boucle par runtime."""

    def test_the_runtime_and_its_factory(self) -> None:
        factory = AsyncioRuntimeFactory()
        assert isinstance(factory, AsyncRuntimeFactory)

        runtime = factory.build(0)
        try:
            assert isinstance(runtime, AsyncRuntime)
        finally:
            runtime.close()

    def test_each_worker_gets_its_own_loop(self) -> None:
        """Deux workers ne partagent pas de boucle : les clients posés dessus seraient
        inutilisables ailleurs."""
        factory = AsyncioRuntimeFactory()
        first, second = factory.build(0), factory.build(1)
        try:
            assert first is not second
            assert first._loop is not second._loop  # noqa: SLF001
        finally:
            first.close()
            second.close()

    def test_close_is_idempotent(self) -> None:
        """Une double fermeture ne doit pas ajouter un second échec au premier."""
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
        """La pile du pool expose bien ``snapshot`` et ``close``."""
        factory = _telemetry_factory()
        assert isinstance(factory, TelemetryFactory)

        runtime = AsyncioRuntimeFactory().build(0)
        try:
            stack = factory.build(0, runtime)
            assert isinstance(stack, WorkerTelemetry)
        finally:
            runtime.close()

    def test_each_worker_gets_its_own_stack(self) -> None:
        """Rien de partagé entre workers, donc rien à verrouiller."""
        factory = _telemetry_factory()
        runtime_factory = AsyncioRuntimeFactory()
        r0, r1 = runtime_factory.build(0), runtime_factory.build(1)

        try:
            first, second = factory.build(0, r0), factory.build(1, r1)

            assert first is not second
            # Des agrégats distincts, sinon la réduction n'aurait aucun sens
            assert (
                first._backends.aggregate  # noqa: SLF001
                is not second._backends.aggregate  # noqa: SLF001
            )
        finally:
            r0.close()
            r1.close()

    def test_an_unknown_reaches_the_aggregate(self) -> None:
        """Un inconnu est routé vers l'agrégat, sinon le bilan le tairait."""
        runtime = AsyncioRuntimeFactory().build(0)
        try:
            stack = _telemetry_factory().build(0, runtime)
            example = UnknownExample(identifier="LEGIARTI000000000001", source_file="")
            stack.record_unknown("balise", "TRUC_INCONNU", example)

            assert stack.snapshot().unknowns == {
                "balise": {"TRUC_INCONNU": UnknownTally(count=1, example=example)}
            }
        finally:
            runtime.close()

    def test_a_collision_reaches_the_aggregate(self) -> None:
        """Une collision déclarée suit le même chemin, vers son propre champ."""
        runtime = AsyncioRuntimeFactory().build(0)
        try:
            stack = _telemetry_factory().build(0, runtime)
            source_files = ("version.xml", "struct.xml")
            stack.record_collision("url", source_files)

            assert stack.snapshot().collisions == {
                "url": CollisionTally(count=1, example=source_files)
            }
        finally:
            runtime.close()
