"""La file de la phase 1 (ADR-034 §3) : la lecture y dépose, le premier worker libre y
prend. Bornée, elle borne la mémoire : au pire 2n + 1 documents vivent à la fois (n
traités, n en file, un en parse).
"""

import queue
import threading
from time import perf_counter

from ragcore.core.models.distribution import Distribution
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.run_measures import RunMeasures
from ragcore.core.statistics_measures import QUEUE_PRODUCER_BLOCKED

__all__ = ["DocumentQueue"]

_POLL_S = 0.5
"""Le délai au bout duquel une attente regarde si le run s'arrête."""

_END = object()
"""Le marqueur de fin : un par worker."""


class DocumentQueue:
    """Les attentes sont mesurées en secondes, pour ``statistics`` (``queues``) : celles
    de la lecture ici, celles des workers par eux (``take``)."""

    def __init__(self, capacity: int) -> None:
        self._queue: queue.Queue[object] = queue.Queue(maxsize=capacity)
        self._stop = threading.Event()
        self._producer_waits: Distribution | None = None

    def stop(self) -> None:
        """Un worker est tombé : la lecture cesse d'attendre une place, et les workers
        d'attendre un document."""
        self._stop.set()

    def offer(self, document: ParsedDocument) -> bool:
        """``False`` si le run s'arrête. Le thread de la lecture seul l'appelle."""
        blocked_s = self._put(document)
        if blocked_s is None:
            return False
        waited = Distribution.of(blocked_s, document.identifier.serialize())
        known = self._producer_waits
        self._producer_waits = waited if known is None else known.merge(waited)
        return True

    def producer_measures(self) -> RunMeasures:
        if self._producer_waits is None:
            return RunMeasures.empty()
        return RunMeasures({QUEUE_PRODUCER_BLOCKED: self._producer_waits})

    def take(self) -> tuple[ParsedDocument | None, float]:
        """``None`` en fin de flux, ou si le run s'arrête."""
        started = perf_counter()
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=_POLL_S)
            except queue.Empty:
                continue
            document = item if isinstance(item, ParsedDocument) else None
            return document, perf_counter() - started
        return None, perf_counter() - started

    def close(self, consumers: int) -> None:
        """Après les documents, y compris quand la lecture échoue : les workers vident
        la file avant de s'arrêter."""
        for _ in range(consumers):
            if self._put(_END) is None:
                return

    def _put(self, item: object) -> float | None:
        started = perf_counter()
        while not self._stop.is_set():
            try:
                self._queue.put(item, timeout=_POLL_S)
            except queue.Full:
                continue
            return perf_counter() - started
        return None
