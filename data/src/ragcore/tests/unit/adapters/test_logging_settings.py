"""``KEDRO_LOG_LEVEL`` : un niveau de ``logging`` en minuscules, ``info`` par défaut."""

import pytest
from pydantic import ValidationError

from ragcore.adapters.config.settings import LoggingSettings

LOG_LEVEL_VAR = "KEDRO_LOG_LEVEL"


@pytest.fixture(autouse=True)
def _sans_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LOG_LEVEL_VAR, raising=False)


def _settings() -> LoggingSettings:
    return LoggingSettings(_env_file=None)  # type: ignore[call-arg]


def test_sans_variable_le_niveau_est_info() -> None:
    assert _settings().log_level == "info"


def test_une_variable_vide_vaut_absente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(LOG_LEVEL_VAR, "")

    assert _settings().log_level == "info"


@pytest.mark.parametrize("value", ["debug", "info", "warning", "error", "critical"])
def test_les_niveaux_de_logging_sont_acceptes(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(LOG_LEVEL_VAR, value)

    assert _settings().log_level == value


@pytest.mark.parametrize("value", ["INFO", "warn", "trace"])
def test_une_autre_valeur_arrete_le_run(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(LOG_LEVEL_VAR, value)

    with pytest.raises(ValidationError, match="log_level"):
        _settings()
