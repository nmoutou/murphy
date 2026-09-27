"""La clôture d'un run : l'ORDRE (raccourcis → drain → bilan → publication → tracker).

Chaque test vise une conséquence observable de cet ordre : ce qui atterrit dans le
bilan persisté, ce qui est publié ou non, et un tracker toujours refermé.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ragcore.adapters.embedding.noop_embedder import NoopEmbedder
from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.application.publish_collection import CollectionPublisher
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.identifiers import OwnerId
from ragcore.core.models.published_collection import PublishedCollection
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.telemetry_events import (
    AUDIT_WRITE_FAILED,
    CHUNK_TRUNCATED,
    DOCUMENT_FETCHED,
    DOCUMENT_PERSISTED,
)
from ragcore.orchestration.kedro.run_session import RunSession
from ragcore.tests.fakes.runtime import FakeRuntime
from ragcore.tests.fakes.telemetry import RecordingTelemetry


class _SpyPublishedRepo:
    def __init__(self) -> None:
        self.published: list[PublishedCollection] = []

    async def publish(self, published: PublishedCollection) -> None:
        self.published.append(published)

    async def get(self) -> PublishedCollection | None:
        return self.published[-1] if self.published else None


class _SpySummaries:
    def __init__(self) -> None:
        self.upserted: list[RunSummary] = []

    async def upsert(self, summary: RunSummary) -> None:
        self.upserted.append(summary)


class _SpyTracker:
    def __init__(self, *, fails_on_log: bool = False) -> None:
        self.logged: list[RunSummary] = []
        self.ended = False
        self._fails_on_log = fails_on_log

    def log_summary(self, summary: RunSummary) -> None:
        if self._fails_on_log:
            raise ConnectionError("backend MLflow injoignable")
        self.logged.append(summary)

    def end_run(self) -> None:
        self.ended = True


class _TruncatingEmbedder(NoopEmbedder):
    @property
    def truncations(self) -> int:
        return 3


class _Spies:
    def __init__(self, stats_dir: Path) -> None:
        self.stats_dir = stats_dir
        self.published = _SpyPublishedRepo()
        self.summaries = _SpySummaries()
        self.telemetry = RecordingTelemetry()


@pytest.fixture
def spies(tmp_path: Path) -> _Spies:
    return _Spies(tmp_path)


@pytest.fixture
def runtime() -> Iterator[FakeRuntime]:
    fake = FakeRuntime(worker_id=-1)
    yield fake
    fake.close()


def _session(
    spies: _Spies,
    runtime: FakeRuntime,
    *,
    tracker: _SpyTracker | None = None,
    embedder: BaseEmbedder | None = None,
) -> RunSession:
    context = PipelineContext.create(owner_id=OwnerId("owner-1"))
    aggregator = RunStatsAggregator(
        run_id=context.run_id,
        owner_id=context.owner_id,
        source=None,
        started_at=datetime.now(UTC),
    )
    for event_type in (DOCUMENT_FETCHED, DOCUMENT_PERSISTED):
        aggregator.emit(build_event(event_type, context.run_id, context.owner_id))
    return RunSession(
        context=context,
        telemetry=spies.telemetry,
        aggregator=aggregator,
        stats_dir=spies.stats_dir,
        summaries=spies.summaries,
        publisher=CollectionPublisher(spies.published, "9424808d", is_full_run=True),
        tracker=tracker or _SpyTracker(),
        embedder=embedder or NoopEmbedder(dimension=768),
        runtime=runtime,
    )


def test_un_run_complet_est_persiste_publie_et_trace(
    spies: _Spies, runtime: FakeRuntime
) -> None:
    tracker = _SpyTracker()

    summary = _session(spies, runtime, tracker=tracker).close(RunStatus.OK)

    assert summary.status is RunStatus.OK
    assert len(list(spies.stats_dir.glob("*.json"))) == 1, (
        "le bilan est écrit en fichier"
    )
    assert spies.summaries.upserted == [summary]
    assert [p.collection_name for p in spies.published.published] == ["9424808d"]
    assert tracker.logged == [summary]
    assert tracker.ended


def test_un_run_casse_ne_publie_pas_mais_ferme_le_tracker(
    spies: _Spies, runtime: FakeRuntime
) -> None:
    tracker = _SpyTracker()

    summary = _session(spies, runtime, tracker=tracker).close(
        RunStatus.FAILED, error_message="nœud connect en panne"
    )

    assert summary.status is RunStatus.FAILED
    assert spies.published.published == []
    assert tracker.ended


def test_une_ecriture_d_audit_perdue_au_drain_degrade_le_bilan_AVANT_publication(
    spies: _Spies,
) -> None:
    """Le drain passe AVANT le bilan : sinon le run serait `ok` sur des compteurs
    qu'on sait incomplets, et publierait."""
    runtime = FakeRuntime(worker_id=-1, drain_failures=2)
    try:
        summary = _session(spies, runtime).close(RunStatus.OK)
    finally:
        runtime.close()

    assert summary.stats.counts[AUDIT_WRITE_FAILED] == 2
    assert summary.status is RunStatus.DEGRADED
    assert spies.published.published == []


def test_les_chunks_raccourcis_se_declarent_meme_sur_un_run_casse(
    spies: _Spies, runtime: FakeRuntime
) -> None:
    session = _session(spies, runtime, embedder=_TruncatingEmbedder(768))

    session.close(RunStatus.FAILED, error_message="panne")

    truncated = spies.telemetry.events_of(CHUNK_TRUNCATED)
    assert [e.payload["count"] for e in truncated] == [3]


def test_le_tracker_se_ferme_meme_quand_log_summary_echoue(
    spies: _Spies, runtime: FakeRuntime
) -> None:
    tracker = _SpyTracker(fails_on_log=True)

    with pytest.raises(ConnectionError):
        _session(spies, runtime, tracker=tracker).close(RunStatus.OK)

    assert tracker.ended
