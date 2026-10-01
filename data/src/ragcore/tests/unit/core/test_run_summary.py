"""RunSummary est la PROJECTION identifiée d'un RunStats.

Ce que ces tests verrouillent : l'identité du run ne participe JAMAIS à
l'agrégation. Elle s'attache une fois, après la réduction. C'est ce qui rend la
fusion des N agrégats de workers commutative — donc le RunSummary déterministe.
"""

import json
from datetime import UTC, datetime

import pytest

from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.core.models.audit import build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.telemetry_events import (
    DOCUMENT_FETCHED,
    DOCUMENT_INVALIDATED,
    DOCUMENT_PERSISTED,
    DOCUMENT_SKIPPED,
)

RUN = RunId("run-1")


@pytest.fixture
def aggregator() -> RunStatsAggregator:
    return RunStatsAggregator(RUN, SourceName.LEGI, datetime.now(UTC))


def test_aggregator_produces_a_valid_summary(aggregator: RunStatsAggregator) -> None:
    summary = aggregator.finalize(RunStatus.OK)

    assert isinstance(summary, RunSummary)
    assert summary.run_id == RUN
    assert summary.status is RunStatus.OK
    assert summary.ended_at >= summary.started_at


def test_counts_reach_the_stats(aggregator: RunStatsAggregator) -> None:
    aggregator.emit(build_event(DOCUMENT_PERSISTED, RUN))
    aggregator.emit(
        build_event(
            DOCUMENT_INVALIDATED,
            RUN,
            payload={"reason": "validation_error"},
            success=False,
        )
    )

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.stats.counts[DOCUMENT_PERSISTED] == 1
    assert summary.stats.counts[DOCUMENT_INVALIDATED] == 1


def test_skipped_files_are_counted_outside_the_equation(
    aggregator: RunStatsAggregator,
) -> None:
    """Un `document.skipped` par raison, porteur de son `count` : le bilan compte les
    fichiers écartés, sans toucher l'équation de complétude."""
    aggregator.emit(build_event(DOCUMENT_FETCHED, RUN, payload={"count": 1}))
    aggregator.emit(build_event(DOCUMENT_PERSISTED, RUN))
    for reason, count in (("export_artifact", 3), ("unreadable", 1)):
        aggregator.emit(
            build_event(
                DOCUMENT_SKIPPED, RUN, payload={"reason": reason, "count": count}
            )
        )

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.stats.counts[DOCUMENT_SKIPPED] == 4
    assert summary.status is RunStatus.OK


def test_status_accepts_the_literals_the_hooks_pass(
    aggregator: RunStatsAggregator,
) -> None:
    """Les hooks passent "ok"/"failed" en chaînes brutes, pas en RunStatus."""
    assert aggregator.finalize("ok").status is RunStatus.OK
    assert aggregator.finalize("failed", "boom").status is RunStatus.FAILED


def test_summary_is_json_serializable() -> None:
    """RunSession écrit summary.model_dump(mode="json") dans un fichier."""
    summary = RunSummary.of(
        RunStats(unknowns={"relation_type": ["titre_tm", "lien_art"]}),
        context_run_id=RUN,
        source=SourceName.CASS,
        started_at=datetime.now(UTC),
        status=RunStatus.OK,
    )

    dumped = json.loads(json.dumps(summary.model_dump(mode="json")))

    assert dumped["source"] == "cass"
    assert dumped["stats"]["unknowns"]["relation_type"] == ["titre_tm", "lien_art"]


def test_source_is_nullable() -> None:
    """L'agrégateur est typé SourceName | None : un run sans source reste légal."""
    summary = RunStatsAggregator(RUN, None, datetime.now(UTC)).finalize(RunStatus.OK)
    assert summary.source is None


def test_unknowns_defaults_to_empty_not_none() -> None:
    """Un run qui a tout compris déclare un vide, pas une absence."""
    summary = RunStatsAggregator(RUN, None, datetime.now(UTC)).finalize(RunStatus.OK)
    assert summary.stats.unknowns == {}


def test_aggregator_declares_what_it_could_not_name(
    aggregator: RunStatsAggregator,
) -> None:
    """Le vocabulaire inconnu remonte jusqu'au sommaire : rien n'est jeté en silence."""
    aggregator.record_unknown("relation_type", "titre_tm")
    aggregator.record_unknown("relation_type", "titre_tm")  # vu deux fois, listé une

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.stats.unknowns["relation_type"] == ["titre_tm"]


def test_the_summary_projects_the_reduction_of_n_workers() -> None:
    """Le cas réel du pool : N agrégats fusionnent, PUIS l'identité s'attache.

    C'est ici que se joue la séparation : ``RunStats`` fusionne parce qu'il n'a
    pas d'identité ; ``RunSummary`` en a une, donc il ne fusionne pas.
    """
    workers = [
        RunStats(counts={DOCUMENT_PERSISTED: 3}, unknowns={"field": ["NOTA"]}),
        RunStats(
            counts={DOCUMENT_PERSISTED: 2}, unknowns={"field": ["NOTA", "CONTENU"]}
        ),
    ]

    summary = RunSummary.of(
        RunStats.reduce(workers),
        context_run_id=RUN,
        source=SourceName.LEGI,
        started_at=datetime.now(UTC),
        status=RunStatus.OK,
    )

    assert summary.stats.counts[DOCUMENT_PERSISTED] == 5
    assert summary.stats.unknowns["field"] == ["NOTA", "CONTENU"]  # union, pas doublon
    assert summary.run_id == RUN  # l'identité vient du contexte, pas des workers
