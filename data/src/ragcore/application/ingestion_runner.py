"""Le pool de la phase 1 : N workers, un seul verrou, celui de la progression.

- Un worker a son runtime, ses clients, ses backends et ses agrégats : rien d'autre de
  mutable n'est partagé.
- Dispatch par clé document : un identifiant n'est traité que par un worker, et le
  ``chunk_id`` dérive de lui, donc deux sagas ne touchent jamais le même chunk.

Le runner ne connaît ni Kedro ni base de données : il ne sait que paralléliser.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from hashlib import blake2b
from typing import Protocol

from ragcore.core.models import ParsedDocument, Relation, RunStats
from ragcore.core.models.audit import build_event
from ragcore.core.models.run_measures import RunMeasures
from ragcore.core.ports.runtime import AsyncRuntime, AsyncRuntimeFactory
from ragcore.core.ports.telemetry import TelemetryFactory, WorkerTelemetry
from ragcore.core.telemetry_events import DOCUMENT_FAILED

from .progress import ProgressLog
from .run_context import PipelineContext

__all__ = [
    "DocumentWorkload",
    "IngestionOutcome",
    "IngestionRunner",
    "WorkerResultsSink",
    "WorkloadResult",
]

_PROGRESS_LABEL = "Phase 1"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkloadResult:
    relations: list[Relation] = field(default_factory=list)
    """Écrites en phase 2, pas ici."""


DocumentWorkload = Callable[
    [ParsedDocument, AsyncRuntime, WorkerTelemetry],
    WorkloadResult,
]


@dataclass(frozen=True)
class IngestionOutcome:
    """La sortie du nœud de phase 1."""

    stats: RunStats
    """Déjà remis à l'agrégat du run : ``report`` n'en lit que les inconnus et les
    collisions."""

    relations: list[Relation]
    """L'entrée de la phase 2."""

    written_node_ids: set[str]
    """Les nœuds écrits par ce run : le delta qui borne le rejeu des pendantes."""

    failures: list[tuple[str, str]]
    """(identifiant, message) des documents dont la saga a échoué."""


class WorkerResultsSink(Protocol):
    """L'agrégat du run, que le hook clôt."""

    def absorb(self, stats: RunStats, measures: RunMeasures) -> None: ...


@dataclass
class _ShardResult:
    relations: list[Relation] = field(default_factory=list)
    written_node_ids: set[str] = field(default_factory=set)
    failures: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class _WorkerSnapshot:
    stats: RunStats
    measures: RunMeasures


@dataclass(frozen=True)
class _PoolRun:
    """Ce que les workers d'un run partagent : le contexte, figé, et deux objets sûrs
    entre threads."""

    context: PipelineContext
    progress: ProgressLog
    snapshots: list[_WorkerSnapshot] = field(default_factory=list)
    """Rempli par chaque worker en sortant, même en échec : ``list.append`` est
    atomique."""


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
        to_process: list[ParsedDocument],
        context: PipelineContext,
        sink: WorkerResultsSink,
    ) -> IngestionOutcome:
        """Synchrone : le pont entre Kedro et les dépôts async.

        Les agrégats des workers rejoignent ``sink`` même quand le pool lève : le bilan
        et les statistiques d'un run en échec gardent ce que la phase 1 a fait.
        """
        pool_run = _PoolRun(context, ProgressLog(_PROGRESS_LABEL, len(to_process)))
        try:
            results = self._run_pool(to_process, pool_run)
        finally:
            stats = _hand_over(pool_run.snapshots, sink)
        pool_run.progress.finish()

        return IngestionOutcome(
            stats=stats,
            relations=[r for shard in results for r in shard.relations],
            written_node_ids=set().union(
                *(shard.written_node_ids for shard in results)
            ),
            failures=[f for shard in results for f in shard.failures],
        )

    def _run_pool(
        self, to_process: list[ParsedDocument], pool_run: _PoolRun
    ) -> list[_ShardResult]:
        shards = self.partition(to_process, self._worker_count)
        with ThreadPoolExecutor(max_workers=self._worker_count) as pool:
            return list(
                pool.map(
                    lambda indexed: self._run_shard(indexed[0], indexed[1], pool_run),
                    enumerate(shards),
                )
            )

    def _run_shard(
        self,
        worker_id: int,
        shard: list[ParsedDocument],
        pool_run: _PoolRun,
    ) -> _ShardResult:
        runtime = self._runtime_factory.build(worker_id)
        telemetry = self._telemetry_factory.build(worker_id, runtime)
        try:
            return self._process(shard, runtime, telemetry, pool_run)
        finally:
            pool_run.snapshots.append(
                _WorkerSnapshot(telemetry.snapshot(), telemetry.snapshot_measures())
            )
            _close_worker(runtime, telemetry)

    def _process(
        self,
        shard: list[ParsedDocument],
        runtime: AsyncRuntime,
        telemetry: WorkerTelemetry,
        pool_run: _PoolRun,
    ) -> _ShardResult:
        result = _ShardResult()
        for parsed in shard:
            identifier = parsed.identifier.serialize()
            pool_run.progress.advance()
            try:
                outcome = self._workload(parsed, runtime, telemetry)
            except Exception as exc:  # noqa: BLE001 — le document est perdu, pas le run : l'échec est compté par document
                _declare_failure(telemetry, parsed, exc, pool_run.context)
                result.failures.append((identifier, str(exc)))
                continue
            result.relations.extend(outcome.relations)
            result.written_node_ids.add(identifier)
        return result

    @staticmethod
    def partition(
        to_process: list[ParsedDocument], worker_count: int
    ) -> list[list[ParsedDocument]]:
        """blake2b plutôt que ``hash()``, randomisé par ``PYTHONHASHSEED`` : la
        partition reste reproductible."""
        shards: list[list[ParsedDocument]] = [[] for _ in range(worker_count)]
        for parsed in to_process:
            shards[_shard_of(parsed.identifier.serialize(), worker_count)].append(
                parsed
            )
        return shards


def _shard_of(identifier: str, worker_count: int) -> int:
    digest = blake2b(identifier.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % worker_count


def _hand_over(snapshots: list[_WorkerSnapshot], sink: WorkerResultsSink) -> RunStats:
    stats = RunStats.reduce(snapshot.stats for snapshot in snapshots)
    sink.absorb(stats, RunMeasures.reduce(s.measures for s in snapshots))
    return stats


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


def _close_worker(runtime: AsyncRuntime, telemetry: WorkerTelemetry) -> None:
    """Les backends d'abord, la boucle ensuite."""
    telemetry.close()
    runtime.close()
