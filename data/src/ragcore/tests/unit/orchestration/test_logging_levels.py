"""``apply_log_level`` règle les loggers du projet et le dit à Kedro."""

import copy
import logging
from collections.abc import Iterator

import pytest
from kedro.framework.project import LOGGING, configure_logging

from ragcore.orchestration.kedro.logging_levels import apply_log_level


@pytest.fixture(autouse=True)
def _restaure_le_logging() -> Iterator[None]:
    saved = copy.deepcopy(LOGGING.data)
    yield
    configure_logging(saved)


def test_les_loggers_du_projet_suivent_le_niveau() -> None:
    apply_log_level("debug")

    for name in ("kedro", "data", "ragcore.saga"):
        assert logging.getLogger(name).getEffectiveLevel() == logging.DEBUG


def test_kedro_garde_la_config_appliquee() -> None:
    """``LOGGING.data`` est réutilisé par Kedro : il doit porter le nouveau niveau."""
    apply_log_level("warning")

    assert LOGGING.data["loggers"]["ragcore"] == {"level": "WARNING"}
    assert "handlers" in LOGGING.data


def test_les_bibliotheques_tierces_ne_bougent_pas() -> None:
    apply_log_level("debug")

    assert logging.getLogger("pymongo").getEffectiveLevel() == logging.WARNING
