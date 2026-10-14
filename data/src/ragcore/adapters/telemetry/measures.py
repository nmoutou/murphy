"""L'agrégat des mesures d'un worker, à côté de celui des compteurs."""

from ragcore.core.models.distribution import Distribution
from ragcore.core.models.run_measures import MeasurePath, RunMeasures

__all__ = ["MeasuresAggregator"]


class MeasuresAggregator:
    """Mutable, contrairement à ``RunStatsAggregator`` : une mesure par étape et par
    document, et recopier le tout à chacune coûterait cher. Sans verrou : un seul thread
    l'écrit, celui de son worker, ou le principal pour celui du hook.
    """

    def __init__(self) -> None:
        self._distributions: dict[MeasurePath, Distribution] = {}

    def record(self, path: MeasurePath, value: float, ref: str) -> None:
        measured = Distribution.of(value, ref)
        known = self._distributions.get(path)
        self._distributions[path] = measured if known is None else known.merge(measured)

    def absorb(self, measures: RunMeasures) -> None:
        self._distributions = dict(self.snapshot().merge(measures).distributions)

    def snapshot(self) -> RunMeasures:
        return RunMeasures(dict(self._distributions))
