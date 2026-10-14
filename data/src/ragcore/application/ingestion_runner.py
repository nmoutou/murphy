"""Le pool de la phase 1 (ADR-034 §3) : une lecture, N workers, une file bornée entre
eux.

- La lecture et le parse restent dans le thread qui appelle ``run`` ; ils déposent dans
  la file, que le premier worker libre consomme.
- Un worker a son runtime, ses clients, ses backends et ses agrégats. Seuls la file, la
  progression et ce que les workers déposent en sortant sont partagés.
- Un identifiant n'est traité que par un worker : la clé est unique par source, et les
  préfixes d'identifiants ne se croisent pas entre sources. Le ``chunk_id`` dérive de
  lui, donc deux sagas ne touchent jamais le même chunk.

Le runner ne connaît ni Kedro ni base de données : il ne sait que paralléliser.
"""

import logging
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol

from ragcore.core.models import ParsedDocument, RunStats
from ragcore.core.models.audit import build_event
from ragcore.core.models.run_measures import RunMeasures
from ragcore.core.ports.runtime import AsyncRuntime, AsyncRuntimeFactory
from ragcore.core.ports.telemetry import TelemetryFactory, WorkerTelemetry
from ragcore.core.statistics_measures import QUEUE_WORKER_IDLE
from ragcore.core.telemetry_events import DOCUMENT_FAILED

from .document_queue import DocumentQueue
from .progress import ProgressLog
from .run_context import PipelineContext

__all__ = [
    "DocumentWorkload",
    "IngestionOutcome",
    "IngestionRunner",
    "WorkerResultsSink",
]

logger = logging.getLogger(__name__)

_PROGRESS_LABEL = "Phase 1"


DocumentWorkload = Callable[[ParsedDocument, AsyncRuntime, WorkerTelemetry], None]
"""Le travail sur un document. Ses relations partent en transit avec lui (ADR-034
§4) : rien n'en remonte."""


@dataclass(frozen=True)
class IngestionOutcome:
    """La sortie du nœud de phase 1."""

    stats: RunStats
    """Déjà remis à l'agrégat du run : ``report`` n'en lit que les inconnus, les
    collisions et les rejets au parse."""

    written_node_ids: set[str]
    """Les nœuds écrits par ce run : le delta qui borne le rejeu des pendantes."""

    failures: list[tuple[str, str]]
    """(identifiant, message) des documents dont la saga a échoué."""


class WorkerResultsSink(Protocol):
    """L'agrégat du run, que le hook clôt."""

    def absorb(self, stats: RunStats, measures: RunMeasures) -> None: ...


@dataclass
class _WorkerResult:
    written_node_ids: set[str] = field(default_factory=set)
    failures: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class _Worker:
    name: str
    runtime: AsyncRuntime
    telemetry: WorkerTelemetry
    result: _WorkerResult = field(default_factory=_WorkerResult)


@dataclass(frozen=True)
class _PoolRun:
    """Ce que la lecture et les workers d'un run partagent. Les listes sont remplies
    par chaque worker en sortant, même en échec : ``list.append`` est atomique."""

    context: PipelineContext
    progress: ProgressLog
    queue: DocumentQueue
    stats: list[RunStats] = field(default_factory=list)
    measures: list[RunMeasures] = field(default_factory=list)
    results: list[_WorkerResult] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)

    def fail(self, exc: Exception) -> None:
        self.errors.append(exc)
        self.queue.stop()

    def hand_in(self, worker: _Worker) -> None:
        self.stats.append(worker.telemetry.snapshot())
        self.measures.append(worker.telemetry.snapshot_measures())
        self.results.append(worker.result)


class IngestionRunner:
    def __init__(
        self,
        workload: DocumentWorkload,
        runtime_factory: AsyncRuntimeFactory,
        telemetry_factory: TelemetryFactory,
        worker_count: int = 4,
    ) -> None:
        if worker_count < 1:
            raise ValueError("worker_count doit valoir au moins 1")
        self._workload = workload
        self._runtime_factory = runtime_factory
        self._telemetry_factory = telemetry_factory
        self._worker_count = worker_count

    def run(
        self,
        documents: Iterable[ParsedDocument],
        context: PipelineContext,
        sink: WorkerResultsSink,
        expected: int | None = None,
    ) -> IngestionOutcome:
        """Synchrone : le pont entre Kedro et les dépôts async. ``documents`` est
        consommé dans le thread appelant ; ``expected`` sert à la progression.

        Les agrégats des workers rejoignent ``sink`` même quand le pool lève : le bilan
        et les statistiques d'un run en échec gardent ce que la phase 1 a fait. Une
        erreur de worker hors document est relevée ici.
        """
        pool_run = _PoolRun(
            context,
            ProgressLog(_PROGRESS_LABEL, expected),
            DocumentQueue(self._worker_count),
        )
        workers = self._start_workers(pool_run)
        try:
            _produce(documents, pool_run)
        finally:
            pool_run.queue.close(self._worker_count)
            for worker in workers:
                worker.join()
            stats = _hand_over(pool_run, sink)
        if pool_run.errors:
            raise pool_run.errors[0]
        pool_run.progress.finish()
        return _outcome(stats, pool_run.results)

    def _start_workers(self, pool_run: _PoolRun) -> list[threading.Thread]:
        workers = [
            threading.Thread(
                target=self._work,
                args=(worker_id, pool_run),
                name=f"ingest-worker-{worker_id}",
            )
            for worker_id in range(self._worker_count)
        ]
        for worker in workers:
            worker.start()
        return workers

    def _work(self, worker_id: int, pool_run: _PoolRun) -> None:
        try:
            self._run_worker(worker_id, pool_run)
        except Exception as exc:  # noqa: BLE001 — frontière du thread : relevée par `run` dans le thread appelant, elle tuerait sinon le worker en silence
            pool_run.fail(exc)

    def _run_worker(self, worker_id: int, pool_run: _PoolRun) -> None:
        worker = self._open_worker(worker_id)
        try:
            self._consume(worker, pool_run)
        finally:
            pool_run.hand_in(worker)
            _close_worker(worker)

    def _open_worker(self, worker_id: int) -> _Worker:
        runtime = self._runtime_factory.build(worker_id)
        try:
            telemetry = self._telemetry_factory.build(worker_id, runtime)
        except Exception:
            runtime.close()
            raise
        return _Worker(f"worker-{worker_id}", runtime, telemetry)

    def _consume(self, worker: _Worker, pool_run: _PoolRun) -> None:
        while True:
            parsed, idle_s = pool_run.queue.take()
            worker.telemetry.record_measure(QUEUE_WORKER_IDLE, idle_s, worker.name)
            if parsed is None:
                return
            pool_run.progress.advance()
            self._process(parsed, worker, pool_run.context)

    def _process(
        self, parsed: ParsedDocument, worker: _Worker, context: PipelineContext
    ) -> None:
        identifier = parsed.identifier.serialize()
        try:
            self._workload(parsed, worker.runtime, worker.telemetry)
        except Exception as exc:  # noqa: BLE001 — le document est perdu, pas le run : l'échec est compté par document
            _declare_failure(worker.telemetry, parsed, exc, context)
            worker.result.failures.append((identifier, str(exc)))
            return
        worker.result.written_node_ids.add(identifier)


def _produce(documents: Iterable[ParsedDocument], pool_run: _PoolRun) -> None:
    """S'arrête de lire dès qu'un worker est tombé."""
    for parsed in documents:
        if not pool_run.queue.offer(parsed):
            return


def _hand_over(pool_run: _PoolRun, sink: WorkerResultsSink) -> RunStats:
    stats = RunStats.reduce(pool_run.stats)
    measures = RunMeasures.reduce(pool_run.measures)
    sink.absorb(stats, measures.merge(pool_run.queue.producer_measures()))
    return stats


def _outcome(stats: RunStats, results: list[_WorkerResult]) -> IngestionOutcome:
    return IngestionOutcome(
        stats=stats,
        written_node_ids=set().union(*(result.written_node_ids for result in results)),
        failures=[f for result in results for f in result.failures],
    )


def _declare_failure(
    telemetry: WorkerTelemetry,
    parsed: ParsedDocument,
    exc: Exception,
    context: PipelineContext,
) -> None:
    """Le document est perdu, pas le run, mais il est compté.

    Le log est la seule trace de quel document a échoué : le bilan n'en garde que le
    compte. La `reason` est le type de l'exception, qui regroupe les échecs ; le message
    reste dans `error`.
    """
    logger.error(
        "document.failed %s (%s) : %s",
        parsed.identifier.serialize(),
        type(exc).__name__,
        exc,
    )
    telemetry.emit(
        build_event(
            event_type=DOCUMENT_FAILED,
            run_id=context.run_id,
            source=parsed.source,
            document_id=parsed.identifier.serialize(),
            payload={"reason": type(exc).__name__, "error": str(exc)},
            success=False,
            error_message=str(exc),
        )
    )


def _close_worker(worker: _Worker) -> None:
    """Les backends d'abord, la boucle ensuite."""
    worker.telemetry.close()
    worker.runtime.close()
