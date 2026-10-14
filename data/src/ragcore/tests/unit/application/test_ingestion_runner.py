"""Le pool : dispatch par clé document, isolement des workers, un document perdu qui
n'arrête pas le corpus mais reste compté, et des agrégats remis au run même en échec.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest

from ragcore.application.ingestion_runner import IngestionRunner, WorkloadResult
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.run_measures import RunMeasures
from ragcore.core.models.run_stats import RunStats
from ragcore.core.ports.runtime import AsyncRuntimeFactory
from ragcore.core.ports.telemetry import TelemetryFactory, WorkerTelemetry
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED
from ragcore.tests.fakes import (
    FakeRuntimeFactory,
    RecordingTelemetry,
    RecordingTelemetryFactory,
)


def _doc(n: int) -> ParsedDocument:
    return ParsedDocument(
        identifier=Identifier(raw=f"LEGIARTI{n:012d}"),
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title=f"Article {n}",
        content=f"contenu {n}",
        structure={},
        metadata={},
        parsed_at=datetime.now(UTC),
    )


def _workload(parsed, runtime, telemetry) -> WorkloadResult:  # noqa: ANN001
    del runtime
    telemetry.emit(
        build_event(
            DOCUMENT_PERSISTED, "run-1", document_id=parsed.identifier.serialize()
        )
    )
    return WorkloadResult(relations=[])


class _SpySink:
    def __init__(self) -> None:
        self.absorbed: list[tuple[RunStats, RunMeasures]] = []

    def absorb(self, stats: RunStats, measures: RunMeasures) -> None:
        self.absorbed.append((stats, measures))


class _FailingRuntimeFactory(FakeRuntimeFactory):
    """Le worker 1 tombe avant son premier document : une panne hors document."""

    def build(self, worker_id: int):  # noqa: ANN201
        if worker_id == 1:
            raise RuntimeError("boucle introuvable")
        return super().build(worker_id)


def _measuring_workload(parsed, runtime, telemetry) -> WorkloadResult:  # noqa: ANN001
    telemetry.record_measure(("documents", "legi", "chunks"), 2, parsed.identifier.raw)
    return _workload(parsed, runtime, telemetry)


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext.create(sources=(SourceName.LEGI,))


def _runner(workload=_workload, worker_count: int = 4) -> IngestionRunner:  # noqa: ANN001
    return IngestionRunner(
        workload=workload,
        runtime_factory=FakeRuntimeFactory(),
        telemetry_factory=RecordingTelemetryFactory(),
        worker_count=worker_count,
    )


class TestPartition:
    """Le dispatch par clé document."""

    def test_every_document_lands_in_exactly_one_shard(self) -> None:
        docs = [_doc(i) for i in range(50)]

        shards = IngestionRunner.partition(docs, worker_count=4)

        placed = [d.identifier.serialize() for shard in shards for d in shard]
        assert sorted(placed) == sorted(d.identifier.serialize() for d in docs)
        assert len(placed) == len(set(placed))  # aucun document dupliqué

    def test_the_same_identifier_always_lands_on_the_same_worker(self) -> None:
        """Un parent ne va jamais sur deux workers, donc deux sagas ne se croisent
        jamais sur un chunk."""
        first = IngestionRunner.partition([_doc(7)], 4)
        second = IngestionRunner.partition([_doc(7)], 4)

        assert [i for i, s in enumerate(first) if s] == [
            i for i, s in enumerate(second) if s
        ]

    def test_the_dispatch_is_reproducible_across_processes(self) -> None:
        """La partition survit à un changement de ``PYTHONHASHSEED`` : on relance un
        interpréteur neuf."""
        script = (
            "from ragcore.application.ingestion_runner import _shard_of;"
            "print([_shard_of(f'LEGIARTI{i:012d}', 4) for i in range(20)])"
        )
        runs = [
            subprocess.run(  # noqa: S603
                [sys.executable, "-c", script],
                env={**os.environ, "PYTHONHASHSEED": seed},
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            for seed in ("0", "1", "42")
        ]

        assert runs[0] == runs[1] == runs[2]

    def test_a_single_worker_gets_everything(self) -> None:
        docs = [_doc(i) for i in range(10)]
        assert [len(s) for s in IngestionRunner.partition(docs, 1)] == [10]


class TestIsolation:
    """Rien de mutable n'est partagé entre workers."""

    def test_each_worker_gets_its_own_runtime_and_telemetry(
        self, context: PipelineContext
    ) -> None:
        runtime_factory = FakeRuntimeFactory()
        telemetry_factory = RecordingTelemetryFactory()
        runner = IngestionRunner(
            workload=_workload,
            runtime_factory=runtime_factory,
            telemetry_factory=telemetry_factory,
            worker_count=3,
        )

        runner.run([_doc(i) for i in range(9)], context, _SpySink())

        assert len(runtime_factory.built) == 3
        assert len(telemetry_factory.built) == 3
        # Des instances distinctes, pas trois références au même objet
        assert len({id(r) for r in runtime_factory.built}) == 3
        assert len({id(t) for t in telemetry_factory.built}) == 3

    def test_every_worker_closes_its_stack(self, context: PipelineContext) -> None:
        runtime_factory = FakeRuntimeFactory()
        telemetry_factory = RecordingTelemetryFactory()
        runner = IngestionRunner(
            workload=_workload,
            runtime_factory=runtime_factory,
            telemetry_factory=telemetry_factory,
            worker_count=2,
        )

        runner.run([_doc(i) for i in range(6)], context, _SpySink())

        assert all(r.closed for r in runtime_factory.built)
        assert all(t.closed for t in telemetry_factory.built)


class TestOutcome:
    def test_stats_are_the_reduction_of_the_workers(
        self, context: PipelineContext
    ) -> None:
        docs = [_doc(i) for i in range(12)]

        outcome = _runner().run(docs, context, _SpySink())

        # 12 documents, 12 événements, quel que soit le nombre de workers
        assert outcome.stats.counts[DOCUMENT_PERSISTED] == 12
        assert outcome.written_node_ids == {d.identifier.serialize() for d in docs}

    def test_relations_are_collected_not_written(
        self, context: PipelineContext
    ) -> None:
        """La phase 1 remonte les relations sans les écrire."""
        sentinel = object()

        def workload(parsed, runtime, telemetry):  # noqa: ANN001, ANN202
            del parsed, runtime, telemetry
            return WorkloadResult(relations=[sentinel])  # type: ignore[list-item]

        outcome = _runner(workload).run(
            [_doc(i) for i in range(5)], context, _SpySink()
        )

        assert outcome.relations == [sentinel] * 5

    def test_a_failed_document_does_not_stop_the_corpus(
        self, context: PipelineContext
    ) -> None:
        """Un document perdu est compté, sans interrompre le run."""

        def workload(parsed, runtime, telemetry):  # noqa: ANN001, ANN202
            del runtime, telemetry
            if parsed.identifier.raw.endswith("003"):
                raise RuntimeError("saga compensée")
            return WorkloadResult()

        outcome = _runner(workload).run(
            [_doc(i) for i in range(6)], context, _SpySink()
        )

        assert len(outcome.failures) == 1
        identifier, message = outcome.failures[0]
        assert identifier.endswith("003")
        assert "saga compensée" in message
        # Le document échoué ne compte pas comme écrit
        assert identifier not in outcome.written_node_ids
        assert len(outcome.written_node_ids) == 5

    def test_an_empty_corpus_is_a_legal_run(self, context: PipelineContext) -> None:
        outcome = _runner().run([], context, _SpySink())

        assert outcome.relations == []
        assert outcome.written_node_ids == set()
        assert outcome.failures == []


class TestHandOver:
    """Les agrégats des workers rejoignent le run, même quand le pool lève."""

    def test_the_sink_receives_the_reduced_stats_and_measures(
        self, context: PipelineContext
    ) -> None:
        sink = _SpySink()

        _runner(_measuring_workload).run([_doc(i) for i in range(7)], context, sink)

        ((stats, measures),) = sink.absorbed
        assert stats.counts[DOCUMENT_PERSISTED] == 7
        assert measures.distributions[("documents", "legi", "chunks")].count == 7

    def test_a_worker_down_outside_a_document_still_hands_over_the_others(
        self, context: PipelineContext
    ) -> None:
        sink = _SpySink()
        runner = IngestionRunner(
            workload=_workload,
            runtime_factory=_FailingRuntimeFactory(),
            telemetry_factory=RecordingTelemetryFactory(),
            worker_count=2,
        )
        docs = [_doc(i) for i in range(10)]
        handled_by_worker_0 = IngestionRunner.partition(docs, 2)[0]

        with pytest.raises(RuntimeError, match="boucle introuvable"):
            runner.run(docs, context, sink)

        ((stats, _measures),) = sink.absorbed
        assert stats.counts.get(DOCUMENT_PERSISTED, 0) == len(handled_by_worker_0)


def test_worker_count_must_be_at_least_one() -> None:
    with pytest.raises(ValueError, match="au moins 1"):
        IngestionRunner(
            workload=_workload,
            runtime_factory=FakeRuntimeFactory(),
            telemetry_factory=RecordingTelemetryFactory(),
            worker_count=0,
        )


def test_the_doubles_are_substitutable_for_the_real_ports() -> None:
    """Les adaptateurs de production satisfont les ports utilisés ici."""
    assert isinstance(RecordingTelemetry(), WorkerTelemetry)
    assert isinstance(RecordingTelemetryFactory(), TelemetryFactory)
    assert isinstance(FakeRuntimeFactory(), AsyncRuntimeFactory)
