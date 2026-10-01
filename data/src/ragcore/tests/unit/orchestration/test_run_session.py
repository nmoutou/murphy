"""La clôture d'un run : l'ORDRE (raccourcis → drain → bilan).

Chaque test vise une conséquence observable de cet ordre : ce qui atterrit dans le
bilan persisté.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.telemetry_events import (
    AUDIT_WRITE_FAILED,
    CHUNK_TRUNCATED,
    DOCUMENT_FETCHED,
    DOCUMENT_PERSISTED,
)
from ragcore.orchestration.kedro.run_session import RunSession
from ragcore.tests.fakes.embedder import NoopEmbedder
from ragcore.tests.fakes.runtime import FakeRuntime
from ragcore.tests.fakes.telemetry import RecordingTelemetry


class _SpySummaries:
    def __init__(self) -> None:
        self.upserted: list[RunSummary] = []

    async def upsert(self, summary: RunSummary) -> None:
        self.upserted.append(summary)


class _TruncatingEmbedder(NoopEmbedder):
    @property
    def truncations(self) -> int:
        return 3


class _Spies:
    def __init__(self) -> None:
        self.summaries = _SpySummaries()
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
    aggregator = RunStatsAggregator(
        run_id=context.run_id,
        sources=context.sources,
        started_at=datetime.now(UTC),
    )
    for event_type in (DOCUMENT_FETCHED, DOCUMENT_PERSISTED):
        aggregator.emit(build_event(event_type, context.run_id))
    return RunSession(
        context=context,
        telemetry=spies.telemetry,
        aggregator=aggregator,
        summaries=spies.summaries,
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


def test_une_ecriture_d_audit_perdue_au_drain_degrade_le_bilan(
    spies: _Spies,
) -> None:
    """Le drain passe AVANT le bilan : sinon le run serait `ok` sur des compteurs
    qu'on sait incomplets."""
    runtime = FakeRuntime(worker_id=-1, drain_failures=2)
    try:
        summary = _session(spies, runtime).close(RunStatus.OK)
    finally:
        runtime.close()

    assert summary.counts[AUDIT_WRITE_FAILED] == 2
    assert summary.status is RunStatus.DEGRADED


def test_les_chunks_raccourcis_se_declarent_meme_sur_un_run_casse(
    spies: _Spies, runtime: FakeRuntime
) -> None:
    session = _session(spies, runtime, embedder=_TruncatingEmbedder(768))

    session.close(RunStatus.FAILED, error_message="panne")

    truncated = spies.telemetry.events_of(CHUNK_TRUNCATED)
    assert [e.payload["count"] for e in truncated] == [3]
