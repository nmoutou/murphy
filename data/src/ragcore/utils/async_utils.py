"""Gestion persistante de la boucle asyncio pour les contexts synchrones Kedro."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_LOOP: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
    return _LOOP


def close_loop() -> None:
    """Fermer la boucle persistante. Appelé depuis after_pipeline_run / on_pipeline_error."""
    global _LOOP
    if _LOOP is not None and not _LOOP.is_closed():
        _drain_pending_tasks(_LOOP)
        _LOOP.close()
    _LOOP = None


def _drain_pending_tasks(loop: asyncio.AbstractEventLoop) -> None:
    """Attendre les tasks fire-and-forget (écritures télémétrie) avant de fermer la boucle."""
    pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
    if not pending:
        return
    try:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except RuntimeError:
        # Boucle déjà en cours d'exécution ou fermeture — rien à faire.
        return


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Pont entre une coroutine async et un contexte synchrone Kedro.

    Utilise une seule boucle persistante pour tout le pipeline run de sorte que
    les clients async (Motor, Neo4j async, Qdrant async) créés dans
    before_pipeline_run restent liés à une boucle vivante sur tous les nœuds.
    """
    return _get_loop().run_until_complete(coro)
