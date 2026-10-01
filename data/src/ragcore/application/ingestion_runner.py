"""IngestionRunner — le pool de la phase 1. N workers, aucun verrou (§11).

Le verrou disparaît par CONSTRUCTION, pas par discipline :

- *Invariant 1* — un worker = un runtime = une boucle + ses clients + ses backends
  + son agrégat local. Rien de mutable n'est partagé, donc il n'y a rien à
  protéger. La fabrique (``TelemetryFactory``) est ce qui rend cet isolement
  possible : injecter une *instance* aurait fait réapparaître le verrou ailleurs.

- *Invariant 2* — dispatch PAR CLÉ DOCUMENT. Un identifiant donné n'est traité que
  par UN worker. Comme le ``chunk_id`` dérive de l'identifiant du parent, deux
  sagas ne peuvent pas se marcher dessus sur le même chunk : la garantie vient de
  la PARTITION, pas d'un mutex.

Le runner ne connaît ni Kedro, ni DataCatalog, ni base de données : il ne sait que
paralléliser. Le modèle de concurrence n'est donc pas prisonnier de l'orchestrateur
— on peut le lancer depuis un test, un CLI ou un service.
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
    """Ce qu'un worker rapporte après avoir traité UN document."""

    relations: list[Relation] = field(default_factory=list)
    """Les relations extraites — elles ne sont PAS écrites ici (§11 : phase 2)."""


# Le travail sur un document, injecté : le runner ne sait ni chunker, ni embedder,
# ni persister. Il reçoit une fonction, et il la parallélise.
DocumentWorkload = Callable[
    [ParsedDocument, AsyncRuntime, WorkerTelemetry],
    WorkloadResult,
]


@dataclass(frozen=True)
class IngestionOutcome:
    """La sortie du node de phase 1 — de la DONNÉE, pas un effet de bord de hook.

    Le hook ne voit pas les workers : il ne peut donc pas fusionner ce qu'il ne
    voit pas. C'est le node qui réduit ses N agrégats locaux et les retourne ici.
    """

    stats: RunStats
    """Réduction (monoïde) des N agrégats locaux — sans section critique."""

    relations: list[Relation]
    """L'union des relations extraites. C'est l'entrée de la phase 2."""

    written_node_ids: set[str]
    """Les nœuds écrits par CE run — le delta qui borne le rejeu ciblé (§13)."""

    failures: list[tuple[str, str]]
    """(identifiant, message) des documents dont la saga a échoué et compensé.
    Un document perdu n'arrête pas le corpus ; il n'est pas perdu en silence."""


@dataclass
class _ShardResult:
    """Ce qu'UN worker rapporte de son lot de documents."""

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
        """Synchrone : c'est le pont entre Kedro (sync) et les dépôts (async)."""
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
        """Le travail d'UN worker : sa boucle, ses backends, son agrégat."""
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
        """Dispatch par clé document — l'invariant 2, isolé et testable seul.

        Le hachage est explicite (blake2b) et non le ``hash()`` natif : celui-ci est
        randomisé par ``PYTHONHASHSEED`` d'un processus à l'autre. S'en servir
        rendrait la partition non reproductible — et le test « le dispatch par clé
        tient-il ? » impossible à écrire.
        """
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
    """Le document est perdu, pas le run. Mais il doit être COMPTÉ.

    Cet échec partait auparavant en `telemetry.log()`, donc en console seulement —
    jamais dans l'agrégat. Résultat : le RunSummary annonçait « ok » sur un run qui avait
    perdu 98 documents.

    La `reason` est le TYPE de l'exception, pas son message : le message porte des
    identifiants et des chiffres, il donnerait autant de raisons que d'échecs dans
    `meta_audit_events`. Le type, lui, regroupe — et c'est ce qu'on veut lire : « 98
    fuites, toutes sur le même mur ». Le message reste dans `error`.
    """
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
    """Ferme un worker. L'ordre est un invariant, pas une préférence :

    1. `drain()` — attend les écritures d'audit en vol ET dit combien ont levé. Avant,
       ce compte était jeté : une écriture ratée en contexte async ne produisait rien,
       pas même un log.
    2. `record_audit_failure` — le compte entre dans l'agrégat, donc dans le
       `snapshot()` que le worker rend ensuite, donc dans le bilan du run. Il DOIT
       passer avant `telemetry.close()` : après, la pile est morte.
    3. `telemetry.close()` — ferme les backends.
    4. `runtime.close()` — ferme la boucle, qui n'a plus rien à porter.

    Drainer après avoir fermé la télémétrie « marcherait » (l'agrégat vit en mémoire,
    son close() ne fait rien) — mais ce serait s'appuyer sur un détail d'implémentation
    pour un invariant de correction.
    """
    report = runtime.drain()
    if report.failed:
        telemetry.record_audit_failure(report.failed)
        logger.error(
            "%d écriture(s) d'audit PERDUE(S) au drain d'un worker : le bilan de ce run "
            "est déclaré `degraded`.",
            report.failed,
        )
    telemetry.close()
    runtime.close()
