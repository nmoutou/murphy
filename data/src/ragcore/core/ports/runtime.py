"""Le pont sync→async, mais PAR INSTANCE (§11).

``utils/async_utils.py`` tient une boucle asyncio dans une *variable globale*. Avec
N workers, cette boucle unique redevient un point de sérialisation : tout le monde
s'y presse, et les clients créés dessus ne peuvent pas être isolés par worker.

Ce port dit l'inverse : un worker = un runtime = une boucle + ses clients. Rien
n'est partagé, donc il n'y a rien à verrouiller. La globale ``_LOOP`` meurt le jour
où ``adapters/runtime/asyncio_runtime.py`` implémente ce contrat (lot 3).
"""

from collections.abc import Coroutine
from typing import Any, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class AsyncRuntime(Protocol):
    """Une boucle asyncio et ses clients, propres à *un* worker."""

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Exécute une coroutine jusqu'à son terme sur la boucle de ce worker."""
        ...

    def close(self) -> None:
        """Draine les tâches en vol, puis ferme la boucle.

        Le drain est ce qui donne l'audit *at-least-once* : les écritures de
        télémétrie lancées en fire-and-forget doivent aboutir avant la fermeture,
        sinon un run peut se terminer en ayant perdu la trace de ce qu'il a fait.
        """
        ...


@runtime_checkable
class AsyncRuntimeFactory(Protocol):
    """Fabrique un runtime *neuf* — un par worker, jamais partagé."""

    def build(self, worker_id: int) -> AsyncRuntime: ...
