"""La clôture d'un run : les chunks raccourcis sont déclarés avant le bilan, pour y
figurer, et les statistiques sont écrites, que le run ait réussi ou cassé."""

from collections.abc import Iterator

import pytest

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.run_statistics import RunStatistics
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.telemetry_events import (
    CHUNK_TRUNCATED,
    DOCUMENT_FETCHED,
    DOCUMENT_PERSISTED,
)
from ragcore.orchestration.kedro.run_session import RunSession, start_telemetry
from ragcore.tests.fakes.embedder import NoopEmbedder
from ragcore.tests.fakes.runtime import FakeRuntime
from ragcore.tests.fakes.telemetry import RecordingTelemetry


class _SpySummaries:
    def __init__(self) -> None:
        self.upserted: list[RunSummary] = []

    async def upsert(self, summary: RunSummary) -> None:
        self.upserted.append(summary)


class _SpyStatistics:
    def __init__(self) -> None:
        self.upserted: list[RunStatistics] = []

    async def upsert(self, statistics: RunStatistics) -> None:
        self.upserted.append(statistics)


class _TruncatingEmbedder(NoopEmbedder):
    @property
    def truncations(self) -> int:
        return 3


class _Spies:
    def __init__(self) -> None:
        self.summaries = _SpySummaries()
        self.statistics = _SpyStatistics()
        self.telemetry = RecordingTelemetry()


@pytest.fixture
def spies() -> _Spies:
    return _Spies()


@pytest.fixture
def runtime() -> Iterator[FakeRuntime]:
    fake = FakeRuntime(worker_id=-1)
    yield fake
    fake.close()


def _session(
    spies: _Spies,
    runtime: FakeRuntime,
    *,
    embedder: BaseEmbedder | None = None,
) -> RunSession:
    context = PipelineContext.create()
    _, aggregates = start_telemetry(context)
    for event_type in (DOCUMENT_FETCHED, DOCUMENT_PERSISTED):
        aggregates.stats.emit(build_event(event_type, context.run_id))
    aggregates.measures.record(("documents", "legi", "chunks"), 4, "LEGIARTI1")
    with aggregates.stages.stage("phase1"):
        pass
    return RunSession(
        context=context,
        telemetry=spies.telemetry,
        aggregates=aggregates,
        summaries=spies.summaries,
        statistics=spies.statistics,
        embedder=embedder or NoopEmbedder(dimension=768),
        runtime=runtime,
    )


def test_un_run_complet_est_persiste(spies: _Spies, runtime: FakeRuntime) -> None:
    summary = _session(spies, runtime).close(RunStatus.OK)

    assert summary.status is RunStatus.OK
    assert spies.summaries.upserted == [summary]


def test_un_run_casse_persiste_un_bilan_failed(
    spies: _Spies, runtime: FakeRuntime
) -> None:
    summary = _session(spies, runtime).close(
        RunStatus.FAILED, error_message="nœud connect en panne"
    )

    assert summary.status is RunStatus.FAILED
    assert spies.summaries.upserted == [summary]


def test_les_chunks_raccourcis_se_declarent_meme_sur_un_run_casse(
    spies: _Spies, runtime: FakeRuntime
) -> None:
    session = _session(spies, runtime, embedder=_TruncatingEmbedder(768))

    session.close(RunStatus.FAILED, error_message="panne")

    truncated = spies.telemetry.events_of(CHUNK_TRUNCATED)
    assert [e.payload["count"] for e in truncated] == [3]


@pytest.mark.parametrize("status", [RunStatus.OK, RunStatus.FAILED])
def test_les_statistiques_sont_ecrites_quel_que_soit_le_statut(
    spies: _Spies, runtime: FakeRuntime, status: RunStatus
) -> None:
    session = _session(spies, runtime)

    session.close(status, error_message="panne")

    (statistics,) = spies.statistics.upserted
    document = statistics.to_document()
    assert document["run_id"] == session.context.run_id
    assert set(document["stages_s"]) == {"phase1"}
    assert document["documents"]["legi"]["chunks"]["max"] == 4
