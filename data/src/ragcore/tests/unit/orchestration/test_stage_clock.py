import pytest

from ragcore.orchestration.kedro.stage_clock import StageClock


class _Clock:
    def __init__(self, *ticks: float) -> None:
        self._ticks = list(ticks)

    def __call__(self) -> float:
        return self._ticks.pop(0)


def test_a_stage_measured_twice_adds_up() -> None:
    clock = StageClock(_Clock(0, 2, 10, 13))

    with clock.stage("phase1"):
        pass
    with clock.stage("phase1"):
        pass

    assert clock.durations() == {"phase1": 5}


def test_a_failing_stage_is_still_measured() -> None:
    clock = StageClock(_Clock(0, 4))

    with pytest.raises(RuntimeError), clock.stage("phase2_write"):
        raise RuntimeError("panne")

    assert clock.durations() == {"phase2_write": 4}
