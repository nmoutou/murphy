"""Le pool sans verrou (§11) — les invariants, exécutés.

``ingestion_runner.py`` AFFIRME trois choses dans ses docstrings. Une affirmation
non exécutée n'est pas une garantie, c'est un vœu. Ce fichier les exécute :

1. dispatch par clé document — un identifiant ne va jamais sur deux workers ;
2. isolement — un worker = un runtime = une télémétrie, jamais partagés ;
3. un document perdu n'arrête pas le corpus, et n'est pas perdu en silence.
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
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
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
    """L'invariant 2, isolé : le dispatch par clé document."""

    def test_every_document_lands_in_exactly_one_shard(self) -> None:
        docs = [_doc(i) for i in range(50)]

        shards = IngestionRunner.partition(docs, worker_count=4)

        placed = [d.identifier.serialize() for shard in shards for d in shard]
        assert sorted(placed) == sorted(d.identifier.serialize() for d in docs)
        assert len(placed) == len(set(placed))  # aucun document dupliqué

    def test_the_same_identifier_always_lands_on_the_same_worker(self) -> None:
        """La garantie qui remplace le mutex : deux sagas ne peuvent pas se croiser
        sur un même chunk, parce que le parent ne va jamais sur deux workers.
        """
        first = IngestionRunner.partition([_doc(7)], 4)
        second = IngestionRunner.partition([_doc(7)], 4)

        assert [i for i, s in enumerate(first) if s] == [
            i for i, s in enumerate(second) if s
        ]

    def test_the_dispatch_is_reproducible_across_processes(self) -> None:
        """blake2b, et non ``hash()`` : ce dernier est randomisé par PYTHONHASHSEED.

        Figer la forme de la partition ne prouverait rien — elle serait stable dans
        CE processus même avec ``hash()``. Ce qu'il faut montrer, c'est qu'elle
        survit à un changement de graine : on relance donc un interpréteur neuf.
        """
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
    """L'invariant 1 : rien de mutable n'est partagé, donc rien n'est à protéger."""

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

        runner.run([_doc(i) for i in range(9)], context)

        assert len(runtime_factory.built) == 3
        assert len(telemetry_factory.built) == 3
        # Des INSTANCES distinctes — pas trois références au même objet.
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

        runner.run([_doc(i) for i in range(6)], context)

        assert all(r.closed for r in runtime_factory.built)
        assert all(t.closed for t in telemetry_factory.built)


class TestOutcome:
    def test_stats_are_the_reduction_of_the_workers(
        self, context: PipelineContext
    ) -> None:
        docs = [_doc(i) for i in range(12)]

        outcome = _runner().run(docs, context)

        # 12 documents, 12 événements — quel que soit le nombre de workers.
        assert outcome.stats.counts[DOCUMENT_PERSISTED] == 12
        assert outcome.written_node_ids == {d.identifier.serialize() for d in docs}

    def test_relations_are_collected_not_written(
        self, context: PipelineContext
    ) -> None:
        """La phase 1 EXTRAIT les relations ; elle ne les écrit pas (§11 : phase 2)."""
        sentinel = object()

        def workload(parsed, runtime, telemetry):  # noqa: ANN001, ANN202
            del parsed, runtime, telemetry
            return WorkloadResult(relations=[sentinel])  # type: ignore[list-item]

        outcome = _runner(workload).run([_doc(i) for i in range(5)], context)

        assert outcome.relations == [sentinel] * 5

    def test_a_failed_document_does_not_stop_the_corpus(
        self, context: PipelineContext
    ) -> None:
        """Un document perdu est une donnée, pas une interruption — ni un silence."""

        def workload(parsed, runtime, telemetry):  # noqa: ANN001, ANN202
            del runtime, telemetry
            if parsed.identifier.raw.endswith("003"):
                raise RuntimeError("saga compensée")
            return WorkloadResult()

        outcome = _runner(workload).run([_doc(i) for i in range(6)], context)

        assert len(outcome.failures) == 1
        identifier, message = outcome.failures[0]
        assert identifier.endswith("003")
        assert "saga compensée" in message
        # Le document échoué ne compte PAS comme écrit.
        assert identifier not in outcome.written_node_ids
        assert len(outcome.written_node_ids) == 5

    def test_an_empty_corpus_is_a_legal_run(self, context: PipelineContext) -> None:
        outcome = _runner().run([], context)

        assert outcome.relations == []
        assert outcome.written_node_ids == set()
        assert outcome.failures == []


def test_worker_count_must_be_at_least_one() -> None:
    with pytest.raises(ValueError, match="au moins 1"):
        IngestionRunner(
            workload=_workload,
            runtime_factory=FakeRuntimeFactory(),
            telemetry_factory=RecordingTelemetryFactory(),
            worker_count=0,
        )


def test_the_doubles_are_substitutable_for_the_real_ports() -> None:
    """Sans ce test, tout ce fichier prouverait des propriétés sur des objets que
    la production n'utilise jamais. Le typage étant structurel (Protocol), c'est
    ``isinstance`` qui rend la substituabilité exécutable — pas l'héritage.
    """
    assert isinstance(RecordingTelemetry(), WorkerTelemetry)
    assert isinstance(RecordingTelemetryFactory(), TelemetryFactory)
    assert isinstance(FakeRuntimeFactory(), AsyncRuntimeFactory)
