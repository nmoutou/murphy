"""Le détail des problèmes du run, à côté de leurs comptes dans ``RunStats``."""

from ragcore.core.models.problems import Problem

__all__ = ["ProblemsAggregator"]


class ProblemsAggregator:
    """Mutable, comme ``MeasuresAggregator`` : ``RunStats`` se recopie à chaque
    enregistrement, ce qui serait quadratique sur des dizaines de milliers de détails.
    """

    def __init__(self) -> None:
        self._problems: list[Problem] = []

    def record(self, problem: Problem) -> None:
        self._problems.append(problem)

    def snapshot(self) -> tuple[Problem, ...]:
        return tuple(self._problems)
