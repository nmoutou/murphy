"""``MlflowExperimentTracker`` traduit-il fidèlement le port vers MLflow ?

On n'installe PAS mlflow pour ce test : l'adaptateur l'importe paresseusement
(``import mlflow`` dans ``_mlflow()``), donc un faux module injecté dans
``sys.modules`` est ce que l'adaptateur récupère. Ce faux enregistre chaque appel — on
vérifie alors le **contrat**, pas l'implémentation de MLflow :

- le run-id (le fingerprint) devient le ``run_name`` ET le tag requêtable ;
- la ``WorkflowConfig`` part en clair, aplatie par phase ;
- les compteurs du bilan deviennent des métriques (point → underscore) ;
- le statut est un tag, le vocabulaire non reconnu une métrique de comptage ;
- ``end_run`` ferme, et ne referme pas deux fois.

Ce que ce test ne prouve pas : que le vrai MLflow accepte ces appels. Le faux a la
même *forme*, pas le même *comportement* — mais la forme est tout ce que l'adaptateur
promet de respecter.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

import pytest

from ragcore.adapters.tracking import MlflowExperimentTracker
from ragcore.core.config.workflow import (
    ChunkingConfig,
    EmbeddingConfig,
    NormalizationConfig,
    WorkflowConfig,
)
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary

RUN_ID = RunId("deadbeefcafef00ddeadbeefcafef00d")
OWNER = OwnerId("owner-1")


class _FakeMlflow:
    """Un faux ``mlflow`` qui note ce qu'on lui demande, sans rien exécuter."""

    def __init__(self) -> None:
        self.tracking_uri: str | None = None
        self.experiment: str | None = None
        self.started: dict | None = None
        self.params: dict = {}
        self.metrics: dict[str, float] = {}
        self.tags: dict[str, str] = {}
        self.ended = 0

    def set_tracking_uri(self, uri: str) -> None:
        self.tracking_uri = uri

    def set_experiment(self, name: str) -> None:
        self.experiment = name

    def start_run(self, run_name: str, tags: dict) -> None:
        self.started = {"run_name": run_name, "tags": tags}

    def log_params(self, params: dict) -> None:
        self.params.update(params)

    def log_metric(self, key: str, value: float) -> None:
        self.metrics[key] = value

    def set_tag(self, key: str, value: str) -> None:
        self.tags[key] = value

    def end_run(self) -> None:
        self.ended += 1


@pytest.fixture
def fake_mlflow(monkeypatch: pytest.MonkeyPatch) -> _FakeMlflow:
    fake = _FakeMlflow()
    monkeypatch.setitem(sys.modules, "mlflow", fake)  # type: ignore[arg-type]
    return fake


def _workflow() -> WorkflowConfig:
    return WorkflowConfig(
        normalization=NormalizationConfig(version="none"),
        chunking=ChunkingConfig(strategy="legi-structural-v1", size=128, overlap=25),
        embedding=EmbeddingConfig(model_name="all-mpnet-base-v2", dimension=768),
    )


def _summary(status: RunStatus = RunStatus.OK) -> RunSummary:
    started = datetime(2026, 7, 15, 10, 0, 0, tzinfo=UTC)
    stats = RunStats(
        counts={"document.persisted": 700, "document.failed": 3},
        unknowns={"balise": ["TRUC", "MACHIN"]},
    )
    return RunSummary(
        run_id=RUN_ID,
        owner_id=OWNER,
        source=SourceName.LEGI,
        status=status,
        started_at=started,
        ended_at=started + timedelta(seconds=42),
        stats=stats,
    )


def _tracker() -> MlflowExperimentTracker:
    return MlflowExperimentTracker(tracking_uri="http://mlflow.invalid")


def test_start_run_maps_fingerprint_to_name_and_tag(fake_mlflow: _FakeMlflow) -> None:
    """Le contrat du port : run-id = fingerprint. En MLflow, c'est le ``run_name`` ET
    un tag requêtable — pas l'UUID interne de MLflow.
    """
    tracker = _tracker()
    tracker.start_run(RUN_ID, _workflow())

    assert fake_mlflow.tracking_uri == "http://mlflow.invalid"
    assert fake_mlflow.experiment == "ragcore-ingestion"
    assert fake_mlflow.started is not None
    assert fake_mlflow.started["run_name"] == RUN_ID
    assert fake_mlflow.started["tags"] == {"ragcore.fingerprint": RUN_ID}


def test_start_run_logs_workflow_params_flat(fake_mlflow: _FakeMlflow) -> None:
    """La ``WorkflowConfig`` part EN CLAIR — ce que le hash compresse — aplatie par
    phase pour rester lisible dans l'UI.
    """
    tracker = _tracker()
    tracker.start_run(RUN_ID, _workflow())

    assert fake_mlflow.params["chunking.size"] == 128
    assert fake_mlflow.params["chunking.overlap"] == 25
    assert fake_mlflow.params["chunking.strategy"] == "legi-structural-v1"
    assert fake_mlflow.params["embedding.model_name"] == "all-mpnet-base-v2"
    assert fake_mlflow.params["embedding.dimension"] == 768
    assert fake_mlflow.params["normalization.version"] == "none"


def test_log_summary_turns_counters_into_metrics(fake_mlflow: _FakeMlflow) -> None:
    """Les compteurs du run SONT les métriques. Le point interdit par MLflow devient
    un underscore, sans perte de lisibilité.
    """
    tracker = _tracker()
    tracker.start_run(RUN_ID, _workflow())
    tracker.log_summary(_summary())

    assert fake_mlflow.metrics["document_persisted"] == 700
    assert fake_mlflow.metrics["document_failed"] == 3
    assert fake_mlflow.metrics["duration_seconds"] == 42.0
    # 2 non-reconnus déclarés (TRUC, MACHIN) : le run dit ce qu'il n'a pas compris.
    assert fake_mlflow.metrics["unknowns_total"] == 2
    assert fake_mlflow.tags["ragcore.status"] == "ok"


def test_log_summary_carries_degraded_status(fake_mlflow: _FakeMlflow) -> None:
    tracker = _tracker()
    tracker.start_run(RUN_ID, _workflow())
    tracker.log_summary(_summary(status=RunStatus.DEGRADED))

    assert fake_mlflow.tags["ragcore.status"] == "degraded"


def test_end_run_closes_once(fake_mlflow: _FakeMlflow) -> None:
    """``end_run`` ferme le run — et ne referme pas s'il n'y a rien d'ouvert : sur un
    run jamais démarré, c'est un no-op silencieux.
    """
    tracker = _tracker()
    tracker.start_run(RUN_ID, _workflow())
    tracker.end_run()
    tracker.end_run()  # second appel : le drapeau interne empêche un double end_run

    assert fake_mlflow.ended == 1


def test_end_run_without_start_is_inert(fake_mlflow: _FakeMlflow) -> None:
    tracker = _tracker()
    tracker.end_run()

    assert fake_mlflow.ended == 0
