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

from ..models.drain_report import DrainReport

T = TypeVar("T")


@runtime_checkable
class AsyncRuntime(Protocol):
    """Une boucle asyncio et ses clients, propres à *un* worker."""

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Exécute une coroutine jusqu'à son terme sur la boucle de ce worker."""
        ...

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Lance une coroutine sans l'attendre — le runtime en GARDE la référence.

        C'est la seule façon de lancer une écriture d'audit en fire-and-forget. Un
        appelant qui ferait ``loop.create_task`` lui-même perdrait sa tâche de deux
        façons : le GC peut la ramasser en vol (asyncio n'en tient qu'une référence
        faible), et ``asyncio.all_tasks()`` l'oublie dès qu'elle est terminée — donc
        le drain ne verrait jamais celles qui ont raté *vite*, qui sont justement le
        cas courant d'un backend en panne.
        """
        ...

    def drain(self) -> DrainReport:
        """Attend les tâches en vol et DIT ce qui a raté. Idempotent.

        Le drain est ce qui donne l'audit *at-least-once* : les écritures de
        télémétrie lancées en fire-and-forget doivent aboutir avant la fermeture,
        sinon un run peut se terminer en ayant perdu la trace de ce qu'il a fait.

        Il est SÉPARÉ de ``close()`` parce que son résultat doit pouvoir entrer dans
        le bilan : le hook persiste le ``RunSummary`` **avant** de fermer son runtime,
        et il s'en sert pour l'écrire. Draine-t-on dans ``close()`` seulement, et
        l'échec d'écriture d'audit arrive après le bilan qu'il aurait dû dégrader —
        trop tard, et invisible.

        L'appel reste facultatif : ``close()`` draine encore de lui-même. La séquence
        complète est ``drain()`` → *compter les échecs* → *persister le bilan* →
        ``close()``.
        """
        ...

    def close(self) -> None:
        """Ferme la boucle. Draine d'abord si personne ne l'a fait — sûr par défaut.

        Le compte du drain est alors PERDU (il n'a nulle part où aller) : un appelant
        qui veut voir les écritures ratées appelle ``drain()`` lui-même, avant.
        """
        ...


@runtime_checkable
class AsyncRuntimeFactory(Protocol):
    """Fabrique un runtime *neuf* — un par worker, jamais partagé."""

    def build(self, worker_id: int) -> AsyncRuntime: ...
