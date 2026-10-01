"""Le câblage du bilan : d'un ``IngestionOutcome`` posé au catalogue jusqu'au
``RunSummary`` persisté. Le chemin, pas la formule : le statut se dérivait d'un compteur
que rien n'alimentait, et les tests unitaires restaient verts.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from kedro.io import DataCatalog, MemoryDataset

from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import ResolutionOutcome
from ragcore.core.models.audit import build_event
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus
from ragcore.core.telemetry_events import (
    DOCUMENT_FAILED,
    DOCUMENT_FETCHED,
    DOCUMENT_INVALIDATED,
    DOCUMENT_PERSISTED,
    RELATION_PENDING,
)
from ragcore.orchestration.kedro.nodes.report import report_node


def _aggregator() -> RunStatsAggregator:
    return RunStatsAggregator(
        run_id=RunId("r1"),
        sources=(),
        started_at=datetime.now(UTC),
    )


# --------------------------------------------------------------------------------------
# absorb()
# --------------------------------------------------------------------------------------


def test_an_exclusion_is_not_a_failure() -> None:
    """10 vus = 9 ingérés + 1 exclu ⇒ `ok` : écarter sciemment n'est pas perdre."""
    aggregator = _aggregator()
    aggregator.absorb(
        RunStats(
            counts={
                DOCUMENT_FETCHED: 10,
                DOCUMENT_PERSISTED: 9,
                DOCUMENT_INVALIDATED: 1,
            }
        )
    )

    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.status is RunStatus.OK


def test_a_declared_failure_still_degrades() -> None:
    """Un échec déclaré reste un document perdu : déclaré, il est rejouable, pas
    ingéré."""
    aggregator = _aggregator()
    aggregator.absorb(
        RunStats(
            counts={DOCUMENT_FETCHED: 10, DOCUMENT_PERSISTED: 9, DOCUMENT_FAILED: 1}
        )
    )

    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.status is RunStatus.DEGRADED


def test_the_silent_leak_that_started_all_this() -> None:
    """1121 vus, 1023 ingérés, rien d'autre : l'équation ne demande pas pourquoi, et
    voit la perte."""
    aggregator = _aggregator()
    aggregator.absorb(
        RunStats(counts={DOCUMENT_FETCHED: 1121, DOCUMENT_PERSISTED: 1023})
    )

    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.status is RunStatus.DEGRADED


def test_without_absorb_the_bug_reappears() -> None:
    """Le témoin : sans absorption, le run se déclare `ok` en ayant perdu un document.
    S'il devient rouge, une autre voie de remontée existe : le supprimer sciemment."""
    aggregator = _aggregator()
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.status is RunStatus.OK  # le compteur est vide : rien à dériver


def test_absorb_accumulates_the_workers_counters() -> None:
    """Les `document.persisted` des workers arrivent dans le bilan."""
    aggregator = _aggregator()

    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 600}))
    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 521}))
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.counts[DOCUMENT_PERSISTED] == 1121


def test_absorb_merges_with_what_the_hook_already_saw() -> None:
    """L'agrégat du hook n'est pas écrasé : les deux sources de comptage coexistent."""
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=RunId("r1"),
            source=None,
            payload={"count": 1121},
        )
    )

    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 1121}))
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.counts[DOCUMENT_FETCHED] == 1121
    assert summary.counts[DOCUMENT_PERSISTED] == 1121


def test_failed_is_never_requalified_by_absorption() -> None:
    """Un run qui a levé reste `failed`, même avec des compteurs impeccables."""
    aggregator = _aggregator()
    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 1121}))

    summary = aggregator.finalize(status=RunStatus.FAILED, error_message="boom")

    assert summary.status is RunStatus.FAILED


def test_absorbing_empty_stats_changes_nothing() -> None:
    """Un run qui plante avant la phase 1 absorbe `empty()`."""
    aggregator = _aggregator()
    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 5}))

    aggregator.absorb(RunStats.empty())
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.counts[DOCUMENT_PERSISTED] == 5
    assert summary.status is RunStatus.OK


# --------------------------------------------------------------------------------------
# Le poids des événements de lot
# --------------------------------------------------------------------------------------


def test_a_batch_event_counts_its_payload_not_its_ring() -> None:
    """`document.fetched`, émis une fois pour 1121 documents, vaut 1121."""
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=RunId("r1"),
            source=None,
            payload={"count": 1121},
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_FETCHED] == 1121


def test_an_event_without_count_still_weighs_one() -> None:
    """Un événement par document vaut 1."""
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_PERSISTED,
            run_id=RunId("r1"),
            source=None,
            document_id="x",
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_PERSISTED] == 1


@pytest.mark.parametrize("bogus", ["12", None, -3, 1.5])
def test_a_malformed_count_does_not_break_the_run_report(bogus: object) -> None:
    """Un `count` douteux vaut 1 : le bilan ne doit jamais tomber à cause d'un
    payload."""
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=RunId("r1"),
            source=None,
            payload={"count": bogus},
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_FETCHED] == 1


def test_a_stray_count_on_a_unitary_event_is_IGNORED() -> None:
    """Seuls les événements de ``COUNT_CARRYING_EVENTS`` lisent leur ``count`` :
    ailleurs, il est ignoré et l'événement vaut 1."""
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_PERSISTED,
            run_id=RunId("r1"),
            source=None,
            document_id="x",
            payload={"count": 40},
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_PERSISTED] == 1


# --------------------------------------------------------------------------------------
# Le fil : `report` pousse-t-il vraiment dans l'agrégat du run ?
#
# Kedro libère un MemoryDataset dès son dernier lecteur : `report` est le seul point du
# DAG où les stats des workers existent encore.
# --------------------------------------------------------------------------------------


def _ingestion(stats: RunStats) -> IngestionOutcome:
    return IngestionOutcome(
        stats=stats, relations=[], written_node_ids=set(), failures=[]
    )


def _resolution(stats: RunStats) -> ResolutionOutcome:
    return ResolutionOutcome(
        stats=stats,
        written_count=0,
        pending_count=0,
        reduced_count=0,
        promoted_count=0,
    )


def test_report_node_pushes_the_worker_stats_into_the_run_aggregator() -> None:
    """Le nœud terminal pousse, le hook n'a rien à tirer : la remontée de bout en
    bout."""
    aggregator = _aggregator()

    report_node(
        ingestion_outcome=_ingestion(
            RunStats(
                counts={
                    DOCUMENT_FETCHED: 1124,
                    DOCUMENT_PERSISTED: 1121,
                    DOCUMENT_FAILED: 3,
                }
            )
        ),
        resolution_outcome=_resolution(RunStats(counts={RELATION_PENDING: 19032})),
        to_skip=[],
        run_stats_sink=aggregator,
    )
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.counts[DOCUMENT_PERSISTED] == 1121
    # 3 documents perdus dans les workers : pas de `ok`
    assert summary.status is RunStatus.DEGRADED


def test_the_phase_two_stats_are_not_double_counted() -> None:
    """La phase 2 émet déjà sur la télémétrie du hook : la pousser la compterait deux
    fois."""
    aggregator = _aggregator()

    report_node(
        ingestion_outcome=_ingestion(RunStats.empty()),
        resolution_outcome=_resolution(RunStats(counts={RELATION_PENDING: 19032})),
        to_skip=[],
        run_stats_sink=aggregator,
    )

    assert RELATION_PENDING not in aggregator.snapshot().counts


def test_the_sink_is_the_run_aggregator_itself_not_a_copy() -> None:
    """`copy_mode: assign` au catalogue, sinon `report` pousse dans un clone que
    personne ne finalise."""
    aggregator = _aggregator()

    catalog = DataCatalog({"run_stats_sink": MemoryDataset(copy_mode="assign")})
    catalog.save("run_stats_sink", aggregator)

    assert catalog.load("run_stats_sink") is aggregator
