"""Les durées des étapes du run, pour ``statistics`` (``stages_s``)."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from time import perf_counter

__all__ = ["StageClock"]


class StageClock:
    """Une étape mesurée plusieurs fois s'additionne. Le thread principal seul s'en
    sert : pas de verrou."""

    def __init__(self, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock
        self._seconds: dict[str, float] = {}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        """Mesurée même quand elle lève : un run en échec a aussi ses statistiques."""
        started = self._clock()
        try:
            yield
        finally:
            elapsed = self._clock() - started
            self._seconds[name] = self._seconds.get(name, 0.0) + elapsed

    def durations(self) -> dict[str, float]:
        return dict(self._seconds)
