"""L'identité du run ne participe jamais à l'agrégation : elle s'attache une fois,
après la réduction.
"""

import json
from datetime import UTC, datetime

import pytest

from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.core.models.audit import build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally
from ragcore.core.telemetry_events import (
    DOCUMENT_FETCHED,
    DOCUMENT_INVALIDATED,
    DOCUMENT_PERSISTED,
    DOCUMENT_SUPERSEDED,
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
    """Un compteur par raison : le bilan compte les fichiers écartés, hors équation de
    complétude."""
    aggregator.emit(build_event(DOCUMENT_FETCHED, RUN, payload={"count": 1}))
    aggregator.emit(build_event(DOCUMENT_PERSISTED, RUN))
    skipped = {
        DOCUMENT_VERSION_SKIPPED: 3,
        DOCUMENT_UNREADABLE: 1,
        DOCUMENT_SUPERSEDED: 2,
    }
    for event_type, count in skipped.items():
        aggregator.emit(build_event(event_type, RUN, payload={"count": count}))

    summary = aggregator.finalize(RunStatus.OK)

    assert {key: summary.counts[key] for key in skipped} == skipped
    assert summary.collisions == {}
    assert summary.status is RunStatus.OK


def test_status_accepts_the_literals_the_hooks_pass(
    aggregator: RunStatsAggregator,
) -> None:
    """Les hooks passent "ok"/"failed" en chaînes brutes."""
    assert aggregator.finalize("ok").status is RunStatus.OK
    assert aggregator.finalize("failed", "boom").status is RunStatus.FAILED


def _stored(summary: RunSummary) -> dict[str, object]:
    """Le document tel que ``MongoRunSummaryRepository.upsert`` l'écrit."""
    dumped: dict[str, object] = json.loads(
        json.dumps(summary.model_dump(mode="json", exclude_none=True))
    )
    return dumped


def test_the_stored_summary_is_flat() -> None:
    """Compteurs, inconnus et collisions au premier niveau, sans enveloppe ni
    ventilation."""
    summary = RunSummary.of(
        RunStats(
            counts={DOCUMENT_PERSISTED: 2},
            unknowns={
                "relation_type": {"titre_tm": UnknownTally(count=2, example=DOC_1)}
            },
            collisions={"metadata": 3},
            invalidations={"facet_root_duplicated": 4},
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
    assert stored["collisions"] == {"metadata": 3}
    assert stored["invalidations"] == {"facet_root_duplicated": 4}
    assert "stats" not in stored
    assert "breakdowns" not in stored


def test_an_empty_error_is_not_stored(aggregator: RunStatsAggregator) -> None:
    """Pas de ``error_message: null`` : ``status`` dit déjà que le run n'a pas levé."""
    assert "error_message" not in _stored(aggregator.finalize(RunStatus.OK))
    assert _stored(aggregator.finalize(RunStatus.FAILED, "boom"))["error_message"] == (
        "boom"
    )


def test_sources_list_every_ingested_source() -> None:
    sources = (SourceName.CASS, SourceName.JADE, SourceName.LEGI)

    summary = RunStatsAggregator(RUN, sources, datetime.now(UTC)).finalize(RunStatus.OK)

    assert summary.sources == sources


def test_unknowns_defaults_to_empty_not_none() -> None:
    """Chaque catégorie est présente, même vide : le schéma du bilan est stable
    (ADR-024)."""
    summary = RunStatsAggregator(RUN, (), datetime.now(UTC)).finalize(RunStatus.OK)
    assert summary.unknowns == {"tags": {}, "roots": {}, "links": {}}
    assert summary.collisions == {}


def test_aggregator_declares_what_it_could_not_name(
    aggregator: RunStatsAggregator,
) -> None:
    """Le vocabulaire inconnu remonte jusqu'au bilan."""
    aggregator.record_unknown("relation_type", "titre_tm", DOC_2)
    aggregator.record_unknown("relation_type", "titre_tm", DOC_1)  # deux documents

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.unknowns["relation_type"] == {
        "titre_tm": UnknownTally(count=2, example=DOC_1)
    }


def test_aggregator_counts_collisions_apart_from_unknowns(
    aggregator: RunStatsAggregator,
) -> None:
    """Une collision a son propre champ, au premier niveau, compté par raison."""
    aggregator.record_collision("metadata")
    aggregator.record_collision("metadata")

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.collisions == {"metadata": 2}
    assert "collisions" not in summary.unknowns


def test_aggregator_counts_invalidations_by_reason(
    aggregator: RunStatsAggregator,
) -> None:
    aggregator.record_invalidation("identifier_missing")
    aggregator.record_invalidation("identifier_missing")
    aggregator.record_invalidation("parse_error")

    summary = aggregator.finalize(RunStatus.OK)

    assert summary.invalidations == {"identifier_missing": 2, "parse_error": 1}


def test_the_summary_projects_the_reduction_of_n_workers() -> None:
    """N agrégats fusionnent, puis l'identité s'attache."""
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


def test_a_partial_run_says_how_much_it_read() -> None:
    """Un run `ok` à 10 % ne doit pas passer pour un run complet (ADR-034 §9)."""
    aggregator = RunStatsAggregator(RUN, (SourceName.LEGI,), datetime.now(UTC))
    aggregator.record_inventories(
        {SourceName.LEGI: SourceInventory(total=2116313, retained=211632, ratio=0.1)}
    )

    document = json.loads(aggregator.finalize(RunStatus.OK).model_dump_json())

    assert document["sampling"] == {
        "legi": {"total": 2116313, "retained": 211632, "ratio": 0.1}
    }


def test_a_summary_written_before_the_sampling_still_reads() -> None:
    document = json.loads(
        RunStatsAggregator(RUN, (), datetime.now(UTC))
        .finalize(RunStatus.OK)
        .model_dump_json()
    )
    del document["sampling"]

    summary = RunSummary.model_validate(document)

    assert summary.sampling == {}


def test_a_summary_with_a_single_ratio_still_reads() -> None:
    """Avant les ratios par source : un `ingestion_ratio` au premier niveau, et un
    `sampling` sans ratio, relu à 1."""
    document = json.loads(
        RunStatsAggregator(RUN, (), datetime.now(UTC))
        .finalize(RunStatus.OK)
        .model_dump_json()
    )
    document["ingestion_ratio"] = 0.1
    document["sampling"] = {"legi": {"total": 10, "retained": 1}}

    summary = RunSummary.model_validate(document)

    assert summary.sampling == {
        SourceName.LEGI: SourceInventory(total=10, retained=1, ratio=1)
    }


def test_a_summary_written_before_the_invalidations_still_reads() -> None:
    document = json.loads(
        RunStatsAggregator(RUN, (), datetime.now(UTC))
        .finalize(RunStatus.OK)
        .model_dump_json()
    )
    del document["invalidations"]

    assert RunSummary.model_validate(document).invalidations == {}
