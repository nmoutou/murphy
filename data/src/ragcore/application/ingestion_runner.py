"""Le pool de la phase 1 : N workers, aucun verrou, par construction.

- Un worker a son runtime, ses clients, ses backends et son agrégat : rien de mutable
  n'est partagé.
- Dispatch par clé document : un identifiant n'est traité que par un worker, et le
  ``chunk_id`` dérive de lui, donc deux sagas ne touchent jamais le même chunk.

Le runner ne connaît ni Kedro ni base de données : il ne sait que paralléliser.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from hashlib import blake2b

from ragcore.core.models import ParsedDocument, Relation, RunStats
from ragcore.core.models.audit import build_event
from ragcore.core.ports.runtime import AsyncRuntime, AsyncRuntimeFactory
from ragcore.core.ports.telemetry import TelemetryFactory, WorkerTelemetry
from ragcore.core.telemetry_events import DOCUMENT_FAILED

from .run_context import PipelineContext

__all__ = ["DocumentWorkload", "IngestionOutcome", "IngestionRunner", "WorkloadResult"]

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
    """La sortie du nœud de phase 1. Le hook ne voit pas les workers : c'est le nœud
    qui réduit leurs agrégats et les rend ici.
    """

    stats: RunStats

    relations: list[Relation]
    """L'entrée de la phase 2."""

    written_node_ids: set[str]
    """Les nœuds écrits par ce run : le delta qui borne le rejeu des pendantes."""

    failures: list[tuple[str, str]]
    """(identifiant, message) des documents dont la saga a échoué."""


@dataclass
class _ShardResult:
    relations: list[Relation] = field(default_factory=list)
    written_node_ids: set[str] = field(default_factory=set)
    failures: list[tuple[str, str]] = field(default_factory=list)
    stats: RunStats = field(default_factory=RunStats.empty)


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
    ) -> IngestionOutcome:
        """Synchrone : le pont entre Kedro et les dépôts async."""
        shards = self.partition(to_process, self._worker_count)

        with ThreadPoolExecutor(max_workers=self._worker_count) as pool:
            results = list(
                pool.map(
                    lambda indexed: self._run_shard(indexed[0], indexed[1], context),
                    enumerate(shards),
                )
            )

        return IngestionOutcome(
            stats=RunStats.reduce(shard.stats for shard in results),
            relations=[r for shard in results for r in shard.relations],
            written_node_ids=set().union(
                *(shard.written_node_ids for shard in results)
            ),
            failures=[f for shard in results for f in shard.failures],
        )

    def _run_shard(
        self,
        worker_id: int,
        shard: list[ParsedDocument],
        context: PipelineContext,
    ) -> _ShardResult:
        runtime = self._runtime_factory.build(worker_id)
        telemetry = self._telemetry_factory.build(worker_id, runtime)
        try:
            result = self._process(shard, runtime, telemetry, context)
        finally:
            _close_worker(runtime, telemetry)
        result.stats = telemetry.snapshot()
        return result

    def _process(
        self,
        shard: list[ParsedDocument],
        runtime: AsyncRuntime,
        telemetry: WorkerTelemetry,
        context: PipelineContext,
    ) -> _ShardResult:
        result = _ShardResult()
        for parsed in shard:
            identifier = parsed.identifier.serialize()
            try:
                outcome = self._workload(parsed, runtime, telemetry)
            except Exception as exc:  # noqa: BLE001 — le document est perdu, pas le run : l'échec est compté par document
                _declare_failure(telemetry, parsed, exc, context)
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
