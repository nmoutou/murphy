"""Une ``Distribution`` se fusionne dans n'importe quel ordre : les workers finissent
dans un ordre non déterministe."""

from itertools import permutations

from ragcore.core.models.distribution import Distribution
from ragcore.core.models.run_measures import RunMeasures


def _reduce(values: list[tuple[float, str]]) -> Distribution:
    distributions = [Distribution.of(value, ref) for value, ref in values]
    result = distributions[0]
    for distribution in distributions[1:]:
        result = result.merge(distribution)
    return result


def test_the_summary_figures() -> None:
    distribution = _reduce([(2, "a"), (8, "b"), (5, "c")])

    assert (distribution.count, distribution.sum) == (3, 15)
    assert (distribution.min, distribution.max, distribution.mean) == (2, 8, 5)
    assert distribution.max_ref == "b"


def test_the_merge_does_not_depend_on_the_order() -> None:
    values = [(3, "c"), (9, "b"), (9, "a"), (1, "d")]

    first, *others = [_reduce(list(order)) for order in permutations(values)]

    assert all(other == first for other in others)
    # À maximum égal, la plus petite référence
    assert first.max_ref == "a"


def test_the_document_carries_the_mean() -> None:
    document = _reduce([(1, "a"), (3, "b")]).to_document()

    assert document == {
        "count": 2,
        "sum": 4,
        "min": 1,
        "max": 3,
        "mean": 2,
        "max_ref": "b",
    }


class TestRunMeasures:
    def test_the_merge_adds_up_each_path(self) -> None:
        left = RunMeasures({("documents", "legi", "chunks"): Distribution.of(2, "a")})
        right = RunMeasures({("documents", "legi", "chunks"): Distribution.of(6, "b")})

        merged = left.merge(right)

        assert merged.distributions[("documents", "legi", "chunks")].count == 2
        assert merged == right.merge(left)

    def test_empty_is_neutral(self) -> None:
        measures = RunMeasures({("queues", "worker_idle_s"): Distribution.of(1, "w0")})

        assert RunMeasures.empty().merge(measures) == measures

    def test_the_paths_unfold_into_subdocuments(self) -> None:
        measures = RunMeasures(
            {
                ("documents", "legi", "step_ms", "embed"): Distribution.of(1, "a"),
                ("documents", "legi", "chunks"): Distribution.of(2, "a"),
            }
        )

        document = measures.to_document()

        assert set(document["documents"]["legi"]) == {"step_ms", "chunks"}
        assert document["documents"]["legi"]["step_ms"]["embed"]["max"] == 1
