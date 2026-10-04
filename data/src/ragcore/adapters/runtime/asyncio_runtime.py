"""Une boucle asyncio par instance, donc par worker.

Les clients Motor et Neo4j sont liés à la boucle qui les crée : une boucle partagée
empêcherait de les isoler par worker.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

__all__ = ["AsyncioRuntime", "AsyncioRuntimeFactory"]

T = TypeVar("T")

logger = logging.getLogger(__name__)

DeferredClose = Callable[[], Coroutine[Any, Any, None]]


class AsyncioRuntime:
    """La boucle d'un worker, et le pont sync→async qui va avec."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._deferred_closes: list[DeferredClose] = []

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        return self._loop.run_until_complete(coro)

    def defer_close(self, close: DeferredClose) -> None:
        self._deferred_closes.append(close)

    def close(self) -> None:
        """Idempotent. Les fermetures différées d'abord, de la dernière à la première."""
        if self._loop.is_closed():
            return
        while self._deferred_closes:
            self._run_deferred(self._deferred_closes.pop())
        self._loop.close()

    def _run_deferred(self, close: DeferredClose) -> None:
        try:
            self._loop.run_until_complete(close())
        except Exception as exc:  # noqa: BLE001 — une fermeture ratée ne doit pas empêcher les suivantes ni celle de la boucle ; elle est journalisée
            logger.warning("Fermeture d'un client en échec : %r", exc)


class AsyncioRuntimeFactory:
    """Un runtime neuf par worker, jamais deux fois le même."""

    def build(self, worker_id: int) -> AsyncioRuntime:
        del worker_id  # l'isolement ne dépend pas de l'identité du worker
        return AsyncioRuntime()
