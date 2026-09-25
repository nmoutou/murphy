"""Pont : ``TelemetryPort.emit`` (synchrone) → ``AuditRepository.append`` (async Mongo).

Ce module était le dernier consommateur de la boucle globale. Il faisait
``run_async(coro)`` — c'est-à-dire : « va chercher LA boucle, celle que tout le
monde partage ». Il reçoit désormais **son** runtime, celui de son worker.

La différence n'est pas cosmétique. Avec une boucle globale, un client Motor créé
sur cette boucle ne peut pas être utilisé depuis un autre thread : le pool de §11
serait impossible. En injectant le runtime, chaque worker a sa boucle, ses clients,
et il n'y a plus rien à partager — donc plus rien à verrouiller.

L'écriture reste **fire-and-forget** quand une boucle tourne déjà : la télémétrie
observe l'ingestion, elle ne la ralentit pas. C'est ``AsyncRuntime.drain()`` qui
attend les tâches en vol — d'où l'audit *at-least-once*.

Mais attendre ne suffit pas : il faut **compter ce qui rate**. Les deux branches de
``emit`` laissent désormais l'échec se voir — la branche sync en le laissant remonter
(``RegistryAwareTelemetry._deliver`` le compte), la branche async par le
``DrainReport`` que le drain rapporte. Une ligne d'audit perdue en silence rendait
tous les autres compteurs invérifiables.
"""

import asyncio
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.ports.audit_repository import AuditRepository
from ragcore.core.ports.runtime import AsyncRuntime

__all__ = ["MongoAuditTelemetryAdapter"]


class MongoAuditTelemetryAdapter:
    """Synchrone côté appelant ; route vers ``audit_repo.append`` (Motor/async)."""

    def __init__(self, audit_repo: AuditRepository, runtime: AsyncRuntime) -> None:
        self._audit_repo = audit_repo
        self._runtime = runtime

    def emit(self, event: AuditEvent) -> None:
        """Écrit l'event — et LAISSE REMONTER ce qui rate.

        Ce code attrapait l'exception pour la logger en ``warning``. C'était le trou :
        l'écriture était perdue, et personne ne la comptait. Il n'a pas à s'en excuser
        lui-même — son appelant (``RegistryAwareTelemetry._deliver``) isole déjà les
        exceptions de chaque backend **et les compte** en ``audit.write.failed``. Un
        adaptateur qui avale son erreur prive son appelant de la seule information
        qu'il attend de lui.
        """
        coro = self._audit_repo.append(event)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Contexte synchrone (nœud Kedro) : on traverse le pont par NOTRE runtime.
            self._runtime.run(coro)
            return

        # Contexte async (saga) : fire-and-forget, drainé par le runtime.
        #
        # L'échec ne peut PAS remonter ici — la coroutine s'exécutera après ce `return`.
        # C'est `drain()` qui le rattrapera. Encore faut-il que la tâche soit RETENUE :
        # un `loop.create_task` nu la laisse au GC, et `asyncio.all_tasks()` l'oublie
        # sitôt terminée — donc une écriture qui rate *vite* (Mongo refuse la ligne)
        # devenait introuvable avant même le drain. `spawn` la garde.
        self._runtime.spawn(coro)

    def log(self, level: str, message: str, **context: Any) -> None:  # noqa: ARG002
        return
