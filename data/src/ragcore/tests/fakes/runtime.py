"""Une vraie boucle asyncio par worker, portant son ``worker_id`` pour vérifier que
chaque worker a la sienne.
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class FakeRuntime:
    def __init__(self, worker_id: int) -> None:
        self.worker_id = worker_id
        self.closed = False
        self.run_count = 0
        self._loop = asyncio.new_event_loop()
        self._deferred_closes: list[Callable[[], Coroutine[Any, Any, None]]] = []

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        self.run_count += 1
        return self._loop.run_until_complete(coro)

    def defer_close(self, close: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._deferred_closes.append(close)

    def close(self) -> None:
        self.closed = True
        if self._loop.is_closed():
            return
        while self._deferred_closes:
            self._loop.run_until_complete(self._deferred_closes.pop()())
        self._loop.close()


class FakeRuntimeFactory:
    def __init__(self) -> None:
        self.built: list[FakeRuntime] = []

    def build(self, worker_id: int) -> FakeRuntime:
        runtime = FakeRuntime(worker_id)
        self.built.append(runtime)
        return runtime
