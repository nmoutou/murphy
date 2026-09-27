"""La session d'UN run : son état, ouvert en tête de run, clos en fin — sans ``None``.

Le hook Kedro vit le temps du process ; un run, lui, commence dans
``before_pipeline_run`` et finit dans ``after_pipeline_run`` ou ``on_pipeline_error``.
Tout ce qui n'existe que pendant ce run (contexte, télémétrie, agrégat, publieur,
tracker, embedder) est ici, et n'est jamais « pas encore posé » : une session existe
entière ou n'existe pas.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ragcore.adapters.storage.mongo.audit_repository import MongoAuditRepository
from ragcore.adapters.telemetry import (
    JsonlFileTelemetry,
    MongoAuditTelemetryAdapter,
    RunStatsAggregator,
)
from ragcore.adapters.telemetry.factory import assemble_telemetry
from ragcore.adapters.telemetry.registry_aware import RegistryAwareTelemetry
from ragcore.application.publish_collection import CollectionPublisher
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.experiment_tracker import ExperimentTracker
from ragcore.core.ports.run_summary_repository import RunSummaryRepository
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.services.run_artifacts import run_scoped_filename
from ragcore.core.services.telemetry_registry import TelemetryRegistry
from ragcore.core.telemetry_events import CHUNK_TRUNCATED, EVENT_CATALOG
from ragcore.orchestration.kedro.assembly import ReportsTruncations

__all__ = ["RunSession", "start_telemetry"]

logger = logging.getLogger(__name__)


def start_telemetry(
    meta_root: Path,
    context: PipelineContext,
    audit_repo: MongoAuditRepository,
    runtime: AsyncRuntime,
) -> tuple[RegistryAwareTelemetry, RunStatsAggregator]:
    """Monte la pile de télémétrie du run et l'agrégat qui fera son bilan.

    Le registre est construit depuis le catalogue Python — source de vérité unique.
    """
    aggregator = RunStatsAggregator(
        run_id=context.run_id,
        owner_id=context.owner_id,
        source=context.source,
        started_at=context.started_at,
    )
    telemetry = assemble_telemetry(
        TelemetryRegistry.from_catalog(EVENT_CATALOG),
        jsonl=JsonlFileTelemetry(
            events_dir=meta_root / "events",
            run_id=context.run_id,
            started_at=context.started_at,
        ),
        mongo=MongoAuditTelemetryAdapter(audit_repo, runtime),
        aggregate=aggregator,
    )
    return telemetry, aggregator


@dataclass(frozen=True)
class RunSession:
    """L'état d'un run, et les deux gestes du hook sur lui : émettre, clore."""

    context: PipelineContext
    telemetry: TelemetryPort
    aggregator: RunStatsAggregator
    """L'agrégat du run. Le node `report` y POUSSE les stats des workers (il est le
    `run_stats_sink` du catalogue) ; `close` le finalise en bilan."""
    stats_dir: Path
    summaries: RunSummaryRepository
    publisher: CollectionPublisher
    """Publie l'empreinte du run en fin de run, si le bilan dit `ok` (ADR-039)."""
    tracker: ExperimentTracker
    """Le tracker d'expériences (§9), ouvert en tête de run. `close` le ferme dans les
    deux fins de run, pour qu'un run cassé ne laisse pas un run MLflow ouvert que le
    suivant viendrait polluer. `noop` par défaut."""
    embedder: BaseEmbedder
    """Gardé pour l'interroger en fin de run : un chunk qu'il a dû raccourcir pour tenir
    dans la fenêtre du modèle est un chunk dont la fin n'est PAS indexée. Le document est
    sauvé, le run est complet — mais le bilan doit le dire."""
    runtime: AsyncRuntime
    """Le runtime du hook : la session s'en sert, le hook le ferme."""

    def emit_lifecycle_event(
        self,
        event_type: str,
        run_params: dict[str, Any],
        error: Exception | None = None,
    ) -> None:
        """Émet un événement de cycle de vie du run (démarré, terminé, échoué)."""
        payload: dict[str, object] = {
            "pipeline": run_params.get("pipeline_name", "__default__")
        }
        if error is not None:
            payload["error"] = str(error)
        self.telemetry.emit(
            build_event(
                event_type=event_type,
                run_id=self.context.run_id,
                owner_id=self.context.owner_id,
                source=self.context.source,
                payload=payload,
                success=error is None,
                error_message=str(error) if error is not None else None,
            )
        )

    def close(self, status: RunStatus, error_message: str | None = None) -> RunSummary:
        """Clôt le run, qu'il ait réussi ou cassé : l'ORDRE est tout l'enjeu.

        1. Les chunks que l'embedder a dû raccourcir. Le compteur vit sur l'embedder (il
           est le seul à voir le refus du service) et il est lu ICI, une fois, après tous
           les workers. Déclarés AUSSI sur un run cassé : le raccourcissement a bien eu
           lieu, et il pointe une config à corriger. Émis AVANT le drain, pour que
           l'événement soit vidé.
        2. Le drain AVANT le bilan : c'est lui qui révèle les écritures d'audit perdues,
           et un bilan persisté avant de le savoir déclarerait `ok` un run dont il ne
           peut plus prouver la complétude. Sur un run cassé, le statut reste `failed`,
           mais savoir si la trace elle aussi est trouée décide de ce qu'on peut
           conclure du reste.
        3. Le bilan, dont le statut se dérive des compteurs — dont ceux que le node
           `report` a poussés depuis les workers.
        4. SEULEMENT si le run a réussi, la publication : c'est ce que le serving lira.
           Elle est la CONSÉQUENCE du bilan, jamais son présupposé.
        5. Le tracker (§9) reçoit le bilan et le run d'expérience se ferme — toujours,
           sinon le prochain lancement se grefferait sur un run resté ouvert.

        Rend le bilan persisté.
        """
        self._declare_truncations()
        self._drain_and_declare()
        summary = self._persist_summary(status, error_message)
        if status is RunStatus.OK:
            self.runtime.run(self.publisher.publish_if_complete(summary))
        self._track_and_close(summary)
        return summary

    def _declare_truncations(self) -> None:
        """Un chunk raccourci n'est pas une perte, mais ce n'est pas rien : il se DÉCLARE.

        Le document est ingéré (donc l'équation de complétude tombe juste, à raison), mais
        la fin du chunk n'est pas indexée. Un compteur non nul veut dire une seule chose :
        **le `chunk_size` configuré n'est pas compatible avec la fenêtre du modèle**. Le
        run est sauvé ; la configuration, elle, est à corriger.
        """
        if not isinstance(self.embedder, ReportsTruncations):
            return
        truncations = self.embedder.truncations
        if not truncations:
            return
        self.telemetry.emit(
            build_event(
                event_type=CHUNK_TRUNCATED,
                run_id=self.context.run_id,
                owner_id=self.context.owner_id,
                source=self.context.source,
                payload={"count": truncations},
            )
        )
        logger.warning(
            "%d chunk(s) raccourci(s) pour tenir dans la fenêtre du modèle. Le corpus est "
            "complet, mais la fin de ces chunks n'est pas indexée : baisser `chunk_size`.",
            truncations,
        )

    def _drain_and_declare(self) -> None:
        """Attend les écritures d'audit en vol, et DÉCLARE celles qui ont échoué.

        Le compte doit entrer dans l'agrégat AVANT le bilan pour que ``_status_from`` le
        voie. Le drain n'est pas la fermeture : le bilan a encore besoin de la boucle (il
        y écrit le sommaire, de façon *synchrone* : il n'y laisse donc rien en vol).
        C'est bien pour ça que le port sépare ``drain()`` de ``close()``.
        """
        report = self.runtime.drain()
        if not report.failed:
            return
        self.aggregator.record_audit_failure("drain", report.failed)
        logger.error(
            "%d écriture(s) d'audit PERDUE(S) : le bilan de ce run repose sur des "
            "compteurs incomplets — il est déclaré `degraded`.",
            report.failed,
        )

    def _persist_summary(
        self, status: RunStatus, error_message: str | None
    ) -> RunSummary:
        """Finalise l'agrégat et persiste le RunSummary (fichier JSON + Mongo).

        Le statut annoncé n'est **pas** celui qui sort (``finalize`` le re-dérive des
        compteurs). Qui veut savoir si le run est vraiment `ok` — pour publier, par
        exemple — doit lire le bilan, pas ce qu'il a demandé.
        """
        summary = self.aggregator.finalize(status=status, error_message=error_message)
        path = self.stats_dir / run_scoped_filename(
            summary.run_id, summary.started_at, ".json"
        )
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.runtime.run(self.summaries.upsert(summary))
        return summary

    def _track_and_close(self, summary: RunSummary) -> None:
        """Enregistre le bilan dans le tracker, puis ferme le run — **toujours**.

        `end_run` est en `finally` : une exception dans `log_summary` (backend
        injoignable) ne doit pas laisser le run pendant.
        """
        try:
            self.tracker.log_summary(summary)
        finally:
            self.tracker.end_run()
