"""Une boucle asyncio par instance, donc par worker.

Les clients Motor et Neo4j sont liés à la boucle qui les crée : une boucle partagée
empêcherait de les isoler par worker.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

__all__ = ["AsyncioRuntime", "AsyncioRuntimeFactory"]

T = TypeVar("T")


class AsyncioRuntime:
    """La boucle d'un worker, et le pont sync→async qui va avec."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        return self._loop.run_until_complete(coro)

    def close(self) -> None:
        """Idempotent."""
        if self._loop.is_closed():
            return
        self._loop.close()


class AsyncioRuntimeFactory:
    """Un runtime neuf par worker, jamais deux fois le même."""

    def build(self, worker_id: int) -> AsyncioRuntime:
        del worker_id  # l'isolement ne dépend pas de l'identité du worker
        return AsyncioRuntime()
