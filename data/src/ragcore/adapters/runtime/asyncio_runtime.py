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

from ragcore.core.models.drain_report import DrainReport

__all__ = ["AsyncioRuntime", "AsyncioRuntimeFactory"]

T = TypeVar("T")


class AsyncioRuntime:
    """La boucle d'UN worker, et le pont sync→async qui va avec."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._tasks: list[asyncio.Task[Any]] = []
        """Les écritures en vol — RETENUES, sinon le GC ou la boucle les oublient."""

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        return self._loop.run_until_complete(coro)

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Lance une écriture en fire-and-forget — et EN GARDE LA TRACE.

        C'est ici que le runtime cesse d'être un simple porteur de boucle : il possède
        les tâches qu'il a lancées. Deux raisons, et la seconde est le bug qu'on vient
        de trouver.

        1. ``asyncio`` ne tient qu'une référence **faible** aux tâches. Une tâche
           lancée sans être retenue peut être ramassée par le GC **en plein vol** —
           l'écriture d'audit disparaît alors sans jamais s'exécuter. C'est un piège
           documenté d'``asyncio.create_task``.

        2. ``asyncio.all_tasks()`` ne rend que les tâches **non terminées** : une tâche
           finie est retirée du registre de la boucle. Or une écriture d'audit qui rate
           *vite* (Mongo qui refuse la ligne, connexion morte) est **déjà terminée**
           quand le drain regarde. Elle était donc introuvable — et son exception
           partait dans le néant, avec pour seule trace le « Task exception was never
           retrieved » d'asyncio. Le drain ne pouvait pas la compter : il ne pouvait
           même plus la voir.

        Un appelant qui fait ``loop.create_task`` lui-même retombe dans les deux
        pièges. C'est pourquoi l'émission passe par ici.
        """
        self._tasks.append(self._loop.create_task(coro))

    def drain(self) -> DrainReport:
        """Attend les écritures lancées et RAPPORTE celles qui ont levé. Idempotent.

        Le drain EST l'audit at-least-once. Les écritures de télémétrie sont lancées
        en fire-and-forget : fermer la boucle sans les attendre, c'est terminer un run
        en ayant perdu la trace de ce qu'il a fait — et un run qui ment sur son propre
        bilan est pire qu'un run qui échoue.

        ⚠️ Attendre ne suffit pas : il faut REGARDER. ``return_exceptions=True`` ne
        supprime pas les exceptions, il les range dans la liste des résultats — que ce
        code jetait. Une écriture d'audit qui échouait ne produisait donc *rien* : ni
        levée, ni log, ni compteur. Le run se déclarait complet sur des compteurs dont
        une partie n'était jamais arrivée en base.

        On draine ``self._tasks`` et non ``asyncio.all_tasks()`` : celui-ci a déjà
        oublié les tâches terminées, donc précisément celles qui ont raté vite (cf.
        ``spawn``).

        Idempotent : les tâches drainées sont retirées. Un second appel ne recompte pas
        les mêmes échecs — un compteur qui double à chaque appel dégraderait le run sur
        du vent.
        """
        if self._loop.is_closed() or not self._tasks:
            return DrainReport.empty()

        tasks, self._tasks = self._tasks, []
        try:
            results = self._loop.run_until_complete(
                asyncio.gather(*tasks, return_exceptions=True)
            )
        except RuntimeError:
            # Boucle déjà en cours d'exécution ou en fermeture : rien à drainer.
            return DrainReport.empty()

        failed = sum(1 for result in results if isinstance(result, BaseException))
        return DrainReport(drained=len(tasks), failed=failed)

    def close(self) -> None:
        """Ferme la boucle. Draine d'abord — sûr par défaut, même sans ``drain()``.

        Le compte est perdu ici (personne à qui le rendre) : qui veut voir les
        écritures ratées appelle ``drain()`` avant, tant qu'il a encore une pile de
        télémétrie sous la main.
        """
        if self._loop.is_closed():
            return
        self.drain()
        self._loop.close()


class AsyncioRuntimeFactory:
    """Fabrique un runtime NEUF par worker — jamais deux fois le même."""

    def build(self, worker_id: int) -> AsyncioRuntime:
        del worker_id  # l'isolement ne dépend pas de l'identité du worker
        return AsyncioRuntime()
