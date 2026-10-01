"""Le pont sync→async, par worker : une boucle et ses clients chacun, rien de partagé,
donc rien à verrouiller.
"""

from collections.abc import Coroutine
from typing import Any, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class AsyncRuntime(Protocol):
    """Une boucle asyncio et ses clients, propres à *un* worker."""

    def run(self, coro: Coroutine[Any, Any, T]) -> T: ...

    def close(self) -> None:
        """Idempotent."""
        ...


@runtime_checkable
class AsyncRuntimeFactory(Protocol):
    """Un runtime neuf par worker, jamais partagé."""

    def build(self, worker_id: int) -> AsyncRuntime: ...
