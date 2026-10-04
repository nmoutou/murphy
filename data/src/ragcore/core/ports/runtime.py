"""Le pont sync→async, par worker : une boucle et ses clients chacun, rien de partagé,
donc rien à verrouiller.
"""

from collections.abc import Callable, Coroutine
from typing import Any, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class AsyncRuntime(Protocol):
    """Une boucle asyncio et ses clients, propres à *un* worker."""

    def run(self, coro: Coroutine[Any, Any, T]) -> T: ...

    def defer_close(self, close: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """Une fermeture à exécuter dans la boucle, juste avant ``close()`` : un client
        lié à la boucle ne se ferme plus une fois celle-ci fermée."""
        ...

    def close(self) -> None:
        """Idempotent."""
        ...


@runtime_checkable
class AsyncRuntimeFactory(Protocol):
    """Un runtime neuf par worker, jamais partagé."""

    def build(self, worker_id: int) -> AsyncRuntime: ...
