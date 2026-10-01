"""Runtimes factices — une vraie boucle asyncio, mais une par worker et traçable.

Le point du test n'est pas de simuler asyncio (on le laisse faire son travail) :
c'est de pouvoir AFFIRMER que chaque worker a reçu SA boucle, et jamais celle du
voisin. D'où le ``worker_id`` porté par le runtime.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class FakeRuntime:
    def __init__(self, worker_id: int) -> None:
        self.worker_id = worker_id
        self.closed = False
        self.run_count = 0
        self._loop = asyncio.new_event_loop()

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        self.run_count += 1
        return self._loop.run_until_complete(coro)

    def close(self) -> None:
        self.closed = True
        if not self._loop.is_closed():
            self._loop.close()


class FakeRuntimeFactory:
    def __init__(self) -> None:
        self.built: list[FakeRuntime] = []

    def build(self, worker_id: int) -> FakeRuntime:
        runtime = FakeRuntime(worker_id)
        self.built.append(runtime)
        return runtime
