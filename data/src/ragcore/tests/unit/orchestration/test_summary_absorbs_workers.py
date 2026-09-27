"""Le CÂBLAGE du bilan — pas la fonction, le fil.

Ce fichier existe à cause d'un bug précis : `_status_from()` dérivait le statut du
compteur de compensations, ce compteur n'était jamais alimenté (les compensations
arrivent dans les WORKERS, dont l'agrégat ne remontait pas), donc le statut valait
**toujours** `ok`. Le `degraded` avait ses tests unitaires — verts — sur un `RunStats`
fabriqué à la main.

> **Un correctif validé sur un test unitaire ne prouve rien du câblage réel.**

D'où ces tests : ils partent d'un `IngestionOutcome` posé au catalogue (ce que le DAG
produit *vraiment*) et vérifient ce qui atterrit dans le `RunSummary` persisté. Le
chemin, pas la formule.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from kedro.io import DataCatalog, MemoryDataset

from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import ResolutionOutcome
from ragcore.core.models.audit import build_event
from ragcore.core.models.identifiers import OwnerId, RunId
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
        owner_id=OwnerId("default"),
        source=None,
        started_at=datetime.now(UTC),
    )


# --------------------------------------------------------------------------------------
# absorb() — le maillon qui manquait
# --------------------------------------------------------------------------------------


def test_an_exclusion_is_not_a_failure() -> None:
    """10 vus = 9 ingérés + 1 EXCLU ⇒ `ok`. Écarter sciemment n'est pas perdre.

    Un document invalide a été *vu, jugé, et rejeté* — le run en rend compte et n'a rien
    perdu. C'est la frontière entre `invalidated` (une décision) et `failed` (un accident).
    """
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
    """Un échec DÉCLARÉ reste un document perdu. Le déclarer le rend rejouable, pas ingéré.

    C'est la distinction que le statut doit tenir : l'équation vérifie l'HONNÊTETÉ du
    bilan, elle ne transforme pas une perte avouée en succès.
    """
    aggregator = _aggregator()
    aggregator.absorb(
        RunStats(
            counts={DOCUMENT_FETCHED: 10, DOCUMENT_PERSISTED: 9, DOCUMENT_FAILED: 1}
        )
    )

    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.status is RunStatus.DEGRADED


def test_the_silent_leak_that_started_all_this() -> None:
    """**Le cas réel.** 1121 vus, 1023 ingérés, RIEN d'autre — et l'ancien code disait `ok`.

    Les 98 documents manquants avaient échoué AVANT la saga (chunk hors fenêtre du
    modèle) : aucune compensation, donc l'ancien critère ne voyait rien. L'équation, elle,
    ne demande pas *pourquoi* — seulement si le compte tombe juste.
    """
    aggregator = _aggregator()
    aggregator.absorb(
        RunStats(counts={DOCUMENT_FETCHED: 1121, DOCUMENT_PERSISTED: 1023})
    )

    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.status is RunStatus.DEGRADED


def test_without_absorb_the_bug_reappears() -> None:
    """Le témoin. Sans absorption, le run se déclare `ok` en ayant perdu un document.

    Ce test documente le bug plutôt qu'il ne le teste : il fige la raison d'être
    d'`absorb`. S'il devient rouge, c'est qu'on a trouvé une AUTRE voie de remontée —
    et il faudra alors le supprimer sciemment, pas le rafistoler.
    """
    aggregator = _aggregator()
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.status is RunStatus.OK  # le compteur est vide : rien à dériver


def test_absorb_accumulates_the_workers_counters() -> None:
    """Les `document.persisted` des workers arrivent dans le bilan — les 1121 manquants."""
    aggregator = _aggregator()

    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 600}))
    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 521}))
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.stats.counts[DOCUMENT_PERSISTED] == 1121


def test_absorb_merges_with_what_the_hook_already_saw() -> None:
    """L'agrégat du hook n'est pas ÉCRASÉ : les deux sources de comptage coexistent."""
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=RunId("r1"),
            owner_id=OwnerId("default"),
            source=None,
            payload={"count": 1121},
        )
    )

    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 1121}))
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.stats.counts[DOCUMENT_FETCHED] == 1121
    assert summary.stats.counts[DOCUMENT_PERSISTED] == 1121


def test_failed_is_never_requalified_by_absorption() -> None:
    """Un run qui a levé reste `failed`, même si ses compteurs sont impeccables.

    `_status_from` ne s'applique qu'à un statut `ok` en entrée. Absorber les stats d'un
    run planté sert à savoir *jusqu'où* il est allé — pas à le repeindre en vert.
    """
    aggregator = _aggregator()
    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 1121}))

    summary = aggregator.finalize(status=RunStatus.FAILED, error_message="boom")

    assert summary.status is RunStatus.FAILED


def test_absorbing_empty_stats_changes_nothing() -> None:
    """L'élément neutre du monoïde. Un run qui plante avant la phase 1 absorbe `empty()`."""
    aggregator = _aggregator()
    aggregator.absorb(RunStats(counts={DOCUMENT_PERSISTED: 5}))

    aggregator.absorb(RunStats.empty())
    summary = aggregator.finalize(status=RunStatus.OK)

    assert summary.stats.counts[DOCUMENT_PERSISTED] == 5
    assert summary.status is RunStatus.OK


# --------------------------------------------------------------------------------------
# Le poids des events de LOT — `document.fetched: 1` sur un run de 1121 documents
# --------------------------------------------------------------------------------------


def test_a_batch_event_counts_its_payload_not_its_ring() -> None:
    """`document.fetched` est émis UNE fois pour 1121 documents. Il vaut 1121, pas 1.

    Sans ça, le critère de fin (« ingérés + exclus + échoués = total vu ») n'est pas
    vérifiable depuis le RunSummary : le « total vu » y valait 1.
    """
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=RunId("r1"),
            owner_id=OwnerId("default"),
            source=None,
            payload={"count": 1121},
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_FETCHED] == 1121


def test_an_event_without_count_still_weighs_one() -> None:
    """Le cas général ne régresse pas : un event par document vaut 1."""
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_PERSISTED,
            run_id=RunId("r1"),
            owner_id=OwnerId("default"),
            source=None,
            document_id="x",
            payload={"operation": "INSERT"},
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_PERSISTED] == 1


@pytest.mark.parametrize("bogus", ["12", None, -3, 1.5])
def test_a_malformed_count_does_not_break_the_run_report(bogus: object) -> None:
    """Un payload est de la télémétrie, pas un contrat typé. Un `count` douteux vaut 1.

    Le bilan d'un run ne doit jamais tomber à cause de la forme d'un payload : c'est
    précisément quand le run va mal qu'on a besoin de le lire.
    """
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=RunId("r1"),
            owner_id=OwnerId("default"),
            source=None,
            payload={"count": bogus},
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_FETCHED] == 1


def test_a_stray_count_on_a_unitary_event_is_IGNORED() -> None:
    """F15 : le contrat est explicite, pas déduit de la clé.

    Avant, ``_weight_of`` lisait ``payload["count"]`` pour N'IMPORTE quel event, au seul
    motif que la clé s'appelait ``count``. Un ``document.persisted`` (unitaire) qui aurait
    porté un ``count`` parasite aurait pesé ce compte — un document aurait valu 40.
    Désormais seuls les events DÉCLARÉS porteurs (``COUNT_CARRYING_EVENTS``) lisent leur
    payload ; ailleurs, un ``count`` est du bruit et l'event vaut 1.
    """
    aggregator = _aggregator()
    aggregator.emit(
        build_event(
            event_type=DOCUMENT_PERSISTED,
            run_id=RunId("r1"),
            owner_id=OwnerId("default"),
            source=None,
            document_id="x",
            payload={"operation": "INSERT", "count": 40},
        )
    )

    assert aggregator.snapshot().counts[DOCUMENT_PERSISTED] == 1


# --------------------------------------------------------------------------------------
# LE FIL LUI-MÊME : le node `report` pousse-t-il vraiment dans l'agrégat du run ?
#
# Les tests ci-dessus valident `absorb`. Ils étaient verts AVANT le correctif, parce que
# la fonction n'a jamais été en cause : c'est le FIL qui manquait.
#
# Et le premier fil que j'ai posé était FAUX : le hook allait lire `ingestion_outcome` au
# catalogue en `after_pipeline_run`. Kedro **libère** un MemoryDataset dès son dernier
# lecteur (`_release_datasets`) — le `load()` d'après-run tombait donc sur un dataset vide,
# et mon `except: continue` avalait l'erreur. Un run de 1121 documents se déclarait `ok`
# avec un bilan sans un seul `document.persisted`.
#
# D'où ces tests : ils exercent `report_node` LUI-MÊME, le seul point du DAG où les stats
# des workers existent encore.
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
    """**LE test du fil.** Le node terminal pousse ; le hook n'a rien à tirer.

    C'est le seul endroit qui prouve la remontée de bout en bout : `report_node` est
    appelé avec l'agrégat que le hook pose au catalogue, et l'on vérifie le
    `RunSummary` qui en sort.
    """
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

    assert summary.stats.counts[DOCUMENT_PERSISTED] == 1121
    # 3 documents perdus, remontés par les workers ⇒ le run n'a pas le droit de dire `ok`.
    assert summary.status is RunStatus.DEGRADED


def test_the_phase_two_stats_are_not_double_counted() -> None:
    """La phase 2 émet DÉJÀ sur la télémétrie du hook — la pousser la compterait deux fois.

    Mesuré en vrai avant correction : `relation.pending` à 38 064 pour 19 032 réelles.
    Seuls les workers ont un agrégat orphelin ; eux seuls doivent remonter.
    """
    aggregator = _aggregator()

    report_node(
        ingestion_outcome=_ingestion(RunStats.empty()),
        resolution_outcome=_resolution(RunStats(counts={RELATION_PENDING: 19032})),
        to_skip=[],
        run_stats_sink=aggregator,
    )

    assert RELATION_PENDING not in aggregator.snapshot().counts


def test_the_sink_is_the_run_aggregator_itself_not_a_copy() -> None:
    """`copy_mode: assign` au catalogue — sinon le node pousse dans un CLONE.

    Ce test fige la raison d'être de cette ligne du `catalog.yml` : un agrégat copié
    absorberait parfaitement… dans un objet que personne ne finalise.
    """
    aggregator = _aggregator()

    catalog = DataCatalog({"run_stats_sink": MemoryDataset(copy_mode="assign")})
    catalog.save("run_stats_sink", aggregator)

    assert catalog.load("run_stats_sink") is aggregator
