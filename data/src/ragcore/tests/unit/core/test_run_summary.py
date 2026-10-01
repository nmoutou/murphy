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
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally
from ragcore.core.telemetry_events import (
    COLLISION_UNRECORDED,
    DOCUMENT_FETCHED,
    DOCUMENT_INVALIDATED,
    DOCUMENT_PERSISTED,
    DOCUMENT_UNREADABLE,
    DOCUMENT_VERSION_SKIPPED,
)

RUN = RunId("run-1")
DOC_1 = UnknownExample(identifier="LEGIARTI000000000001", source_file="a.xml")
DOC_2 = UnknownExample(identifier="LEGIARTI000000000002", source_file="b.xml")


@pytest.fixture
def aggregator() -> RunStatsAggregator:
    return RunStatsAggregator(RUN, (SourceName.LEGI,), datetime.now(UTC))


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

    assert summary.counts[DOCUMENT_PERSISTED] == 1
    assert summary.counts[DOCUMENT_INVALIDATED] == 1


def test_skipped_files_are_counted_outside_the_equation(
    aggregator: RunStatsAggregator,
) -> None:
    """Un compteur par raison, porteur de son `count` : le bilan compte les fichiers
    écartés, sans toucher l'équation de complétude."""
    aggregator.emit(build_event(DOCUMENT_FETCHED, RUN, payload={"count": 1}))
    aggregator.emit(build_event(DOCUMENT_PERSISTED, RUN))
    for event_type, count in ((DOCUMENT_VERSION_SKIPPED, 3), (DOCUMENT_UNREADABLE, 1)):
        aggregator.emit(build_event(event_type, RUN, payload={"count": count}))

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.counts[DOCUMENT_VERSION_SKIPPED] == 3
    assert summary.counts[DOCUMENT_UNREADABLE] == 1
    assert summary.status is RunStatus.OK


def test_status_accepts_the_literals_the_hooks_pass(
    aggregator: RunStatsAggregator,
) -> None:
    """Les hooks passent "ok"/"failed" en chaînes brutes, pas en RunStatus."""
    assert aggregator.finalize("ok").status is RunStatus.OK
    assert aggregator.finalize("failed", "boom").status is RunStatus.FAILED


def _stored(summary: RunSummary) -> dict[str, object]:
    """Le document tel que ``MongoRunSummaryRepository.upsert`` l'écrit."""
    dumped: dict[str, object] = json.loads(
        json.dumps(summary.model_dump(mode="json", exclude_none=True))
    )
    return dumped


def test_the_stored_summary_is_flat() -> None:
    """Compteurs et inconnus au premier niveau, sans enveloppe ni ventilation."""
    summary = RunSummary.of(
        RunStats(
            counts={DOCUMENT_PERSISTED: 2},
            unknowns={
                "relation_type": {"titre_tm": UnknownTally(count=2, example=DOC_1)}
            },
        ),
        context_run_id=RUN,
        sources=(SourceName.CASS, SourceName.JADE),
        started_at=datetime.now(UTC),
        status=RunStatus.OK,
    )

    stored = _stored(summary)

    assert stored["sources"] == ["cass", "jade"]
    assert stored["counts"] == {DOCUMENT_PERSISTED: 2}
    assert stored["unknowns"] == {
        "relation_type": {
            "titre_tm": {
                "count": 2,
                "example": {"identifier": DOC_1.identifier, "source_file": "a.xml"},
            }
        }
    }
    assert "stats" not in stored
    assert "breakdowns" not in stored


def test_an_empty_error_is_not_stored(aggregator: RunStatsAggregator) -> None:
    """``status`` dit déjà que le run n'a pas levé : un ``error_message: null`` ne dirait
    rien de plus."""
    assert "error_message" not in _stored(aggregator.finalize(RunStatus.OK))
    assert _stored(aggregator.finalize(RunStatus.FAILED, "boom"))["error_message"] == (
        "boom"
    )


def test_sources_list_every_ingested_source() -> None:
    sources = (SourceName.CASS, SourceName.JADE, SourceName.LEGI)

    summary = RunStatsAggregator(RUN, sources, datetime.now(UTC)).finalize(RunStatus.OK)

    assert summary.sources == sources


def test_unrecorded_collisions_degrade_a_complete_run(
    aggregator: RunStatsAggregator,
) -> None:
    """Tout est ingéré, mais le bilan compte des collisions que la collection ne montre
    pas : le run ne peut pas se déclarer complet (ADR-049)."""
    aggregator.emit(build_event(DOCUMENT_FETCHED, RUN, payload={"count": 1}))
    aggregator.emit(build_event(DOCUMENT_PERSISTED, RUN))
    aggregator.emit(build_event(COLLISION_UNRECORDED, RUN, success=False))

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.status is RunStatus.DEGRADED


def test_unknowns_defaults_to_empty_not_none() -> None:
    """Un run qui a tout compris déclare un vide, pas une absence — catégorie par
    catégorie : le schéma du bilan ne varie pas d'un run à l'autre (ADR-048)."""
    summary = RunStatsAggregator(RUN, (), datetime.now(UTC)).finalize(RunStatus.OK)
    assert summary.unknowns == {"tags": {}, "roots": {}, "links": {}, "collisions": {}}


def test_aggregator_declares_what_it_could_not_name(
    aggregator: RunStatsAggregator,
) -> None:
    """Le vocabulaire inconnu remonte jusqu'au sommaire : rien n'est jeté en silence."""
    aggregator.record_unknown("relation_type", "titre_tm", DOC_2)
    aggregator.record_unknown("relation_type", "titre_tm", DOC_1)  # deux documents

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.unknowns["relation_type"] == {
        "titre_tm": UnknownTally(count=2, example=DOC_1)
    }


def test_the_summary_projects_the_reduction_of_n_workers() -> None:
    """Le cas réel du pool : N agrégats fusionnent, PUIS l'identité s'attache.

    C'est ici que se joue la séparation : ``RunStats`` fusionne parce qu'il n'a
    pas d'identité ; ``RunSummary`` en a une, donc il ne fusionne pas.
    """
    workers = [
        RunStats(
            counts={DOCUMENT_PERSISTED: 3},
            unknowns={"field": {"NOTA": UnknownTally(count=1, example=DOC_2)}},
        ),
        RunStats(
            counts={DOCUMENT_PERSISTED: 2},
            unknowns={"field": {"NOTA": UnknownTally(count=4, example=DOC_1)}},
        ),
    ]

    summary = RunSummary.of(
        RunStats.reduce(workers),
        context_run_id=RUN,
        sources=(SourceName.LEGI,),
        started_at=datetime.now(UTC),
        status=RunStatus.OK,
    )

    assert summary.counts[DOCUMENT_PERSISTED] == 5
    assert summary.unknowns["field"] == {"NOTA": UnknownTally(count=5, example=DOC_1)}
    assert summary.run_id == RUN  # l'identité vient du contexte, pas des workers
