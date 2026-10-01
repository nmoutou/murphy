"""Une boucle asyncio PAR INSTANCE — la fin de la globale `_LOOP`.

``utils/async_utils.py`` tenait la boucle dans une variable de module. Une seule
boucle pour tout le pipeline, c'est un point de sérialisation : avec N workers,
tout le monde s'y presse, et les clients Motor/Neo4j créés dessus sont liés à
*elle* — donc impossibles à isoler par worker.

Ici, la boucle est un attribut d'instance. Le pool en construit une par worker via
la fabrique, et il n'y a plus rien à partager — donc plus rien à verrouiller. Le
verrou ne disparaît pas par discipline : il disparaît parce qu'il n'a plus d'objet.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

__all__ = ["AsyncioRuntime", "AsyncioRuntimeFactory"]

T = TypeVar("T")


class AsyncioRuntime:
    """La boucle d'UN worker, et le pont sync→async qui va avec."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        return self._loop.run_until_complete(coro)

    def close(self) -> None:
        """Ferme la boucle. Idempotent : un second appel ne fait rien."""
        if self._loop.is_closed():
            return
        self._loop.close()


class AsyncioRuntimeFactory:
    """Fabrique un runtime NEUF par worker — jamais deux fois le même."""

    def build(self, worker_id: int) -> AsyncioRuntime:
        del worker_id  # l'isolement ne dépend pas de l'identité du worker
        return AsyncioRuntime()
