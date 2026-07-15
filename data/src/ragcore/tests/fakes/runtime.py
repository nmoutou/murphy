"""Runtimes factices — une vraie boucle asyncio, mais une par worker et traçable.

Le point du test n'est pas de simuler asyncio (on le laisse faire son travail) :
c'est de pouvoir AFFIRMER que chaque worker a reçu SA boucle, et jamais celle du
voisin. D'où le ``worker_id`` porté par le runtime.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

from ragcore.core.models.drain_report import DrainReport

T = TypeVar("T")


class FakeRuntime:
    def __init__(self, worker_id: int, drain_failures: int = 0) -> None:
        self.worker_id = worker_id
        self.closed = False
        self.drained = False
        self.run_count = 0
        self.spawned = 0
        self._drain_failures = drain_failures
        """Nombre d'écritures d'audit qu'on FAIT rater au drain.

        C'est le seul moyen de tester le chemin qui compte : en vrai, un échec vient
        d'un Mongo qui refuse une ligne, ce qu'un test unitaire ne peut pas provoquer.
        Ici on le déclare, et on vérifie que le compte remonte jusqu'au bilan.
        """
        self._loop = asyncio.new_event_loop()

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        self.run_count += 1
        return self._loop.run_until_complete(coro)

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Le fake EXÉCUTE au lieu de différer : un test n'a pas de boucle qui tourne.

        L'important n'est pas d'imiter le fire-and-forget, c'est de ne pas laisser la
        coroutine non consommée (Python lèverait un `RuntimeWarning: never awaited`).
        """
        self.spawned += 1
        self._loop.run_until_complete(coro)

    def drain(self) -> DrainReport:
        self.drained = True
        if not self._drain_failures:
            return DrainReport.empty()
        return DrainReport(drained=self._drain_failures, failed=self._drain_failures)

    def close(self) -> None:
        self.closed = True
        if not self._loop.is_closed():
            self._loop.close()


class FakeRuntimeFactory:
    def __init__(self, drain_failures: int = 0) -> None:
        self.built: list[FakeRuntime] = []
        self._drain_failures = drain_failures

    def build(self, worker_id: int) -> FakeRuntime:
        runtime = FakeRuntime(worker_id, drain_failures=self._drain_failures)
        self.built.append(runtime)
        return runtime
