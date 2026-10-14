"""La progression d'une étape longue, dans les logs : un run complet dure des heures."""

import logging
import threading
import time
from collections.abc import Callable

__all__ = ["ProgressLog"]

logger = logging.getLogger(__name__)

_INTERVAL_S = 30.0


class ProgressLog:
    """Une ligne au plus toutes les ``_INTERVAL_S`` secondes. Partagé par les workers,
    d'où le verrou."""

    def __init__(
        self,
        label: str,
        total: int | None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._label = label
        self._total = total
        self._clock = clock
        self._lock = threading.Lock()
        self._done = 0
        self._started = clock()
        self._last_logged = self._started

    def advance(self) -> None:
        with self._lock:
            self._done += 1
            now = self._clock()
            if now - self._last_logged < _INTERVAL_S:
                return
            self._last_logged = now
            done = self._done
        self._log(done, now)

    def finish(self) -> None:
        with self._lock:
            done = self._done
        self._log(done, self._clock())

    def _log(self, done: int, now: float) -> None:
        elapsed = now - self._started
        rate = done / elapsed if elapsed > 0 else 0.0
        of_total = "" if self._total is None else f" / {self._total}"
        logger.info(
            "%s : %d%s documents en %.0f s (%.1f doc/s)",
            self._label,
            done,
            of_total,
            elapsed,
            rate,
        )
