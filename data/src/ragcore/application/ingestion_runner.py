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

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from hashlib import blake2b

from ragcore.core.models import Operation, ParsedDocument, Relation, RunStats
from ragcore.core.ports.runtime import AsyncRuntime, AsyncRuntimeFactory
from ragcore.core.ports.telemetry import TelemetryFactory, WorkerTelemetry

from .run_context import PipelineContext

__all__ = ["DocumentWorkload", "IngestionOutcome", "IngestionRunner", "WorkloadResult"]


@dataclass(frozen=True)
class WorkloadResult:
    """Ce qu'un worker rapporte après avoir traité UN document."""

    relations: list[Relation] = field(default_factory=list)
    """Les relations extraites — elles ne sont PAS écrites ici (§11 : phase 2)."""


# Le travail sur un document, injecté : le runner ne sait ni chunker, ni embedder,
# ni persister. Il reçoit une fonction, et il la parallélise.
DocumentWorkload = Callable[
    [ParsedDocument, Operation, AsyncRuntime, WorkerTelemetry],
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
        to_process: list[tuple[ParsedDocument, Operation]],
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

        relations: list[Relation] = []
        written_node_ids: set[str] = set()
        failures: list[tuple[str, str]] = []
        for shard_relations, shard_nodes, shard_failures, _ in results:
            relations.extend(shard_relations)
            written_node_ids |= shard_nodes
            failures.extend(shard_failures)

        return IngestionOutcome(
            stats=RunStats.reduce(shard_stats for *_, shard_stats in results),
            relations=relations,
            written_node_ids=written_node_ids,
            failures=failures,
        )

    def _run_shard(
        self,
        worker_id: int,
        shard: list[tuple[ParsedDocument, Operation]],
        context: PipelineContext,
    ) -> tuple[list[Relation], set[str], list[tuple[str, str]], RunStats]:
        """Le travail d'UN worker : sa boucle, ses backends, son agrégat."""
        del context  # le workload le porte déjà ; le shard n'en a pas d'usage propre
        runtime = self._runtime_factory.build(worker_id)
        telemetry = self._telemetry_factory.build(worker_id, runtime)

        relations: list[Relation] = []
        written_node_ids: set[str] = set()
        failures: list[tuple[str, str]] = []

        try:
            for parsed, operation in shard:
                identifier = parsed.identifier.serialize()
                try:
                    result = self._workload(parsed, operation, runtime, telemetry)
                except Exception as exc:  # noqa: BLE001
                    # La saga a déjà compensé ; le document est perdu, pas le run.
                    # L'identifiant part avec l'erreur : un échec anonyme est un échec
                    # qu'on ne pourra pas rejouer.
                    telemetry.log(
                        "error",
                        "ingestion.document.failed",
                        identifier=identifier,
                        error=str(exc),
                    )
                    failures.append((identifier, str(exc)))
                    continue
                relations.extend(result.relations)
                written_node_ids.add(identifier)
        finally:
            # Le drain d'abord (at-least-once), la boucle ensuite : fermer la
            # boucle avant les backends perdrait les écritures encore en vol.
            telemetry.close()
            runtime.close()

        return relations, written_node_ids, failures, telemetry.snapshot()

    @staticmethod
    def partition(
        to_process: list[tuple[ParsedDocument, Operation]], worker_count: int
    ) -> list[list[tuple[ParsedDocument, Operation]]]:
        """Dispatch par clé document — l'invariant 2, isolé et testable seul.

        Le hachage est explicite (blake2b) et non le ``hash()`` natif : celui-ci est
        randomisé par ``PYTHONHASHSEED`` d'un processus à l'autre. S'en servir
        rendrait la partition non reproductible — et le test « le dispatch par clé
        tient-il ? » impossible à écrire.
        """
        shards: list[list[tuple[ParsedDocument, Operation]]] = [
            [] for _ in range(worker_count)
        ]
        for parsed, operation in to_process:
            shards[_shard_of(parsed.identifier.serialize(), worker_count)].append(
                (parsed, operation)
            )
        return shards


def _shard_of(identifier: str, worker_count: int) -> int:
    digest = blake2b(identifier.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % worker_count
