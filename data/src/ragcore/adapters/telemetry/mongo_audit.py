"""Bridge: TelemetryPort.emit -> AuditRepository.append (async Mongo write)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.ports.audit_repository import AuditRepository
from ragcore.utils.async_utils import run_async

logger = logging.getLogger(__name__)


class MongoAuditTelemetryAdapter:
    """Synchrone côté appelant ; route vers `audit_repo.append` (Motor/async).

    - En contexte synchrone (hooks Kedro before/after_pipeline_run, nœuds Kedro) :
      utilise `run_async()` pour exécuter l'append sur la boucle persistante.
    - En contexte asynchrone (saga, use cases) : programme la coroutine en
      fire-and-forget sur la boucle courante. Les tâches sont drainées dans
      `_async_utils.close_loop()` avant la fermeture du loop.
    """

    def __init__(self, audit_repo: AuditRepository) -> None:
        self._audit_repo = audit_repo

    def emit(self, event: AuditEvent) -> None:
        coro = self._audit_repo.append(event)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            run_async(coro)
            return
        loop.create_task(coro)

    def log(self, level: str, message: str, **context: Any) -> None:  # noqa: ARG002
        return
