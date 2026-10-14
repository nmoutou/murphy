"""Le pool : une file bornée entre la lecture et les workers, l'isolement des workers, un
document perdu qui n'arrête pas le corpus mais reste compté, des arrêts qui ne pendent
jamais, et des agrégats remis au run même en échec.
"""

import threading
import time
from collections.abc import Iterator
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
from ragcore.core.statistics_measures import QUEUE_PRODUCER_BLOCKED, QUEUE_WORKER_IDLE
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


def _docs(count: int) -> list[ParsedDocument]:
    return [_doc(n) for n in range(count)]


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
    """Les workers nommés tombent avant leur premier document : une panne hors
    document."""

    def __init__(self, failing: set[int]) -> None:
        super().__init__()
        self._failing = failing

    def build(self, worker_id: int):  # noqa: ANN201
        if worker_id in self._failing:
            raise RuntimeError("boucle introuvable")
        return super().build(worker_id)


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


class TestStream:
    """La lecture alimente la file, que les workers vident : la mémoire est bornée."""

    def test_at_most_two_documents_per_worker_wait_or_run(
        self, context: PipelineContext
    ) -> None:
        """n traités, n en file : la lecture n'avance pas plus loin."""
        lock = threading.Lock()
        counts = {"yielded": 0, "finished": 0, "ahead": 0}

        def stream() -> Iterator[ParsedDocument]:
            for parsed in _docs(40):
                with lock:
                    ahead = counts["yielded"] - counts["finished"]
                    counts["ahead"] = max(counts["ahead"], ahead)
                    counts["yielded"] += 1
                yield parsed

        def slow(parsed, runtime, telemetry) -> WorkloadResult:  # noqa: ANN001
            time.sleep(0.005)
            with lock:
                counts["finished"] += 1
            return _workload(parsed, runtime, telemetry)

        _runner(slow, worker_count=2).run(stream(), context, _SpySink())

        assert counts["finished"] == 40
        assert counts["ahead"] <= 2 * 2

    def test_every_document_is_processed_exactly_once(
        self, context: PipelineContext
    ) -> None:
        docs = _docs(50)

        outcome = _runner().run(iter(docs), context, _SpySink())

        assert outcome.stats.counts[DOCUMENT_PERSISTED] == 50
        assert outcome.written_node_ids == {d.identifier.serialize() for d in docs}

    def test_a_single_worker_gets_everything(self, context: PipelineContext) -> None:
        outcome = _runner(worker_count=1).run(iter(_docs(10)), context, _SpySink())

        assert len(outcome.written_node_ids) == 10


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

        runner.run(iter(_docs(9)), context, _SpySink())

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

        runner.run(iter(_docs(6)), context, _SpySink())

        assert all(r.closed for r in runtime_factory.built)
        assert all(t.closed for t in telemetry_factory.built)


class TestOutcome:
    def test_relations_are_collected_not_written(
        self, context: PipelineContext
    ) -> None:
        """La phase 1 remonte les relations sans les écrire."""
        sentinel = object()

        def workload(parsed, runtime, telemetry):  # noqa: ANN001, ANN202
            del parsed, runtime, telemetry
            return WorkloadResult(relations=[sentinel])  # type: ignore[list-item]

        outcome = _runner(workload).run(iter(_docs(5)), context, _SpySink())

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

        outcome = _runner(workload).run(iter(_docs(6)), context, _SpySink())

        assert len(outcome.failures) == 1
        identifier, message = outcome.failures[0]
        assert identifier.endswith("003")
        assert "saga compensée" in message
        # Le document échoué ne compte pas comme écrit
        assert identifier not in outcome.written_node_ids
        assert len(outcome.written_node_ids) == 5

    def test_an_empty_corpus_is_a_legal_run(self, context: PipelineContext) -> None:
        outcome = _runner().run(iter([]), context, _SpySink())

        assert outcome.relations == []
        assert outcome.written_node_ids == set()
        assert outcome.failures == []


class TestStop:
    """Un arrêt ne pend jamais, et laisse ses agrégats au run."""

    def test_a_failing_read_stops_the_run_after_the_queued_documents(
        self, context: PipelineContext
    ) -> None:
        def stream() -> Iterator[ParsedDocument]:
            yield from _docs(3)
            raise ValueError("lecture cassée")

        sink = _SpySink()
        runtime_factory = FakeRuntimeFactory()
        runner = IngestionRunner(
            workload=_workload,
            runtime_factory=runtime_factory,
            telemetry_factory=RecordingTelemetryFactory(),
            worker_count=2,
        )

        with pytest.raises(ValueError, match="lecture cassée"):
            runner.run(stream(), context, sink)

        ((stats, _measures),) = sink.absorbed
        assert stats.counts[DOCUMENT_PERSISTED] == 3
        assert all(r.closed for r in runtime_factory.built)

    def test_a_worker_down_outside_a_document_stops_the_read(
        self, context: PipelineContext
    ) -> None:
        """Le worker 1 tombe : la lecture cesse d'attendre une place dans la file, et
        les agrégats du worker 0 rejoignent le run."""
        sink = _SpySink()
        runner = IngestionRunner(
            workload=_workload,
            runtime_factory=_FailingRuntimeFactory({1}),
            telemetry_factory=RecordingTelemetryFactory(),
            worker_count=2,
        )

        with pytest.raises(RuntimeError, match="boucle introuvable"):
            runner.run(iter(_docs(1000)), context, sink)

        ((stats, _measures),) = sink.absorbed
        assert stats.counts.get(DOCUMENT_PERSISTED, 0) < 1000

    def test_every_worker_down_does_not_hang_the_read(
        self, context: PipelineContext
    ) -> None:
        """Personne ne vide la file : sans arrêt, la lecture attendrait pour
        toujours."""
        runner = IngestionRunner(
            workload=_workload,
            runtime_factory=_FailingRuntimeFactory({0, 1}),
            telemetry_factory=RecordingTelemetryFactory(),
            worker_count=2,
        )

        with pytest.raises(RuntimeError, match="boucle introuvable"):
            runner.run(iter(_docs(100)), context, _SpySink())


class TestHandOver:
    """Les agrégats des workers et de la file rejoignent le run."""

    def test_the_sink_receives_the_reduced_stats_and_measures(
        self, context: PipelineContext
    ) -> None:
        def measuring(parsed, runtime, telemetry) -> WorkloadResult:  # noqa: ANN001
            telemetry.record_measure(("documents", "legi", "chunks"), 2, "x")
            return _workload(parsed, runtime, telemetry)

        sink = _SpySink()

        _runner(measuring).run(iter(_docs(7)), context, sink)

        ((stats, measures),) = sink.absorbed
        assert stats.counts[DOCUMENT_PERSISTED] == 7
        assert measures.distributions[("documents", "legi", "chunks")].count == 7

    def test_the_queue_waits_are_measured(self, context: PipelineContext) -> None:
        """Une attente par document déposé, une par document pris ou fin de flux."""
        sink = _SpySink()

        _runner(worker_count=2).run(iter(_docs(5)), context, sink)

        ((_stats, measures),) = sink.absorbed
        assert measures.distributions[QUEUE_PRODUCER_BLOCKED].count == 5
        assert measures.distributions[QUEUE_WORKER_IDLE].count == 5 + 2


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
