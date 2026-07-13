"""Pont : ``TelemetryPort.emit`` (synchrone) → ``AuditRepository.append`` (async Mongo).

Ce module était le dernier consommateur de la boucle globale. Il faisait
``run_async(coro)`` — c'est-à-dire : « va chercher LA boucle, celle que tout le
monde partage ». Il reçoit désormais **son** runtime, celui de son worker.

La différence n'est pas cosmétique. Avec une boucle globale, un client Motor créé
sur cette boucle ne peut pas être utilisé depuis un autre thread : le pool de §11
serait impossible. En injectant le runtime, chaque worker a sa boucle, ses clients,
et il n'y a plus rien à partager — donc plus rien à verrouiller.

L'écriture reste **fire-and-forget** quand une boucle tourne déjà : la télémétrie
observe l'ingestion, elle ne la ralentit pas. C'est ``AsyncRuntime.close()`` qui
draine les tâches en vol — d'où l'audit *at-least-once*.
"""

import asyncio
import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.ports.audit_repository import AuditRepository
from ragcore.core.ports.runtime import AsyncRuntime

__all__ = ["MongoAuditTelemetryAdapter"]

_LOGGER = logging.getLogger(__name__)


class MongoAuditTelemetryAdapter:
    """Synchrone côté appelant ; route vers ``audit_repo.append`` (Motor/async)."""

    def __init__(self, audit_repo: AuditRepository, runtime: AsyncRuntime) -> None:
        self._audit_repo = audit_repo
        self._runtime = runtime

    def emit(self, event: AuditEvent) -> None:
        coro = self._audit_repo.append(event)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Contexte synchrone (nœud Kedro) : on traverse le pont par NOTRE runtime.
            try:
                self._runtime.run(coro)
            except Exception as exc:
                _LOGGER.warning("audit mongo: écriture impossible (%s)", exc)
            return

        # Contexte async (saga) : fire-and-forget, drainé à la fermeture du runtime.
        loop.create_task(coro)

    def log(self, level: str, message: str, **context: Any) -> None:  # noqa: ARG002
        return
