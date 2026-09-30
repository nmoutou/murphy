"""Le service TEI, lu de l'environnement."""

import pytest
from pydantic import ValidationError

from ragcore.adapters.config.settings import (
    DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS,
    EmbeddingRuntimeSettings,
)

TIMEOUT_VAR = "EMBEDDING_INGESTION_TIMEOUT"
REQUIRED_VARS = {
    "EMBEDDING_MODEL": "sentence-transformers/all-mpnet-base-v2",
    "EMBEDDING_SERVICE_URL": "http://localhost:5001/v1",
}


@pytest.fixture(autouse=True)
def _required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED_VARS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv(TIMEOUT_VAR, raising=False)


def _settings() -> EmbeddingRuntimeSettings:
    return EmbeddingRuntimeSettings(_env_file=None)  # type: ignore[call-arg]


def test_le_modele_et_l_url_viennent_de_l_environnement() -> None:
    settings = _settings()

    assert settings.model == REQUIRED_VARS["EMBEDDING_MODEL"]
    assert settings.service_url == REQUIRED_VARS["EMBEDDING_SERVICE_URL"]


@pytest.mark.parametrize("name", sorted(REQUIRED_VARS))
def test_une_variable_obligatoire_absente_est_refusee(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.delenv(name)

    with pytest.raises(ValidationError):
        _settings()


@pytest.mark.parametrize("name", sorted(REQUIRED_VARS))
def test_une_variable_obligatoire_vide_est_refusee(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """``EMBEDDING_MODEL=`` dans un ``.env`` donne ``''`` : l'absence, pas une valeur."""
    monkeypatch.setenv(name, "")

    with pytest.raises(ValidationError):
        _settings()


def test_sans_variable_le_timeout_vaut_deux_minutes() -> None:
    assert _settings().ingestion_timeout == DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS


def test_le_timeout_vient_de_l_environnement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TIMEOUT_VAR, "30000")

    assert _settings().ingestion_timeout == 30_000


def test_le_timeout_du_backend_ne_s_applique_pas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``EMBEDDING_SERVICE_TIMEOUT`` règle le backend, qui n'embarque qu'une question."""
    monkeypatch.setenv("EMBEDDING_SERVICE_TIMEOUT", "10000")

    assert _settings().ingestion_timeout == DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS


@pytest.mark.parametrize("value", ["0", "-1", "deux"])
def test_un_timeout_invalide_est_refuse(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(TIMEOUT_VAR, value)

    with pytest.raises(ValidationError, match="ingestion_timeout"):
        _settings()
