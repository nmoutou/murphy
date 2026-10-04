"""``ENVIRONMENT`` : ``dev`` ou ``prod``, et le défaut penche vers le refus."""

import pytest
from pydantic import ValidationError

from ragcore.adapters.config.settings import InfraSettings

ENVIRONMENT_VAR = "ENVIRONMENT"


@pytest.fixture(autouse=True)
def _required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENSEARCH_INDEX", "documents")
    monkeypatch.delenv(ENVIRONMENT_VAR, raising=False)


def _settings() -> InfraSettings:
    return InfraSettings(_env_file=None)  # type: ignore[call-arg]


def test_sans_variable_l_environnement_est_la_prod() -> None:
    assert _settings().environment == "prod"


def test_une_variable_vide_vaut_absente(monkeypatch: pytest.MonkeyPatch) -> None:
    """``ENVIRONMENT=`` dans un ``.env`` donne ``''`` : l'absence, pas une coquille."""
    monkeypatch.setenv(ENVIRONMENT_VAR, "")

    assert _settings().environment == "prod"


@pytest.mark.parametrize("value", ["dev", "prod"])
def test_dev_et_prod_sont_acceptes(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(ENVIRONMENT_VAR, value)

    assert _settings().environment == value


@pytest.mark.parametrize("value", ["Dev", "development", "production", "staging"])
def test_une_autre_valeur_arrete_le_run(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Une coquille n'est pas prise pour la prod : elle arrête le run."""
    monkeypatch.setenv(ENVIRONMENT_VAR, value)

    with pytest.raises(ValidationError, match="environment"):
        _settings()
