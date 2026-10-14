"""La progression ne loggue qu'à intervalle, quel que soit le débit."""

import logging

import pytest

from ragcore.application.progress import ProgressLog


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_one_line_per_interval_at_most(caplog: pytest.LogCaptureFixture) -> None:
    clock = _Clock()
    progress = ProgressLog("Phase 1", total=100, clock=clock)

    with caplog.at_level(logging.INFO, logger="ragcore.application.progress"):
        for _ in range(10):
            progress.advance()
        clock.now = 31
        progress.advance()
        progress.advance()

    (record,) = caplog.records
    assert record.getMessage() == "Phase 1 : 11 / 100 documents en 31 s (0.4 doc/s)"


def test_finish_logs_the_final_count(caplog: pytest.LogCaptureFixture) -> None:
    clock = _Clock()
    progress = ProgressLog("Phase 1", total=None, clock=clock)
    progress.advance()
    clock.now = 2

    with caplog.at_level(logging.INFO, logger="ragcore.application.progress"):
        progress.finish()

    (record,) = caplog.records
    assert record.getMessage() == "Phase 1 : 1 documents en 2 s (0.5 doc/s)"
