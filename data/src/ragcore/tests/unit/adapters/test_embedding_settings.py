"""Le transport de l'embedding, lu de l'environnement."""

import pytest
from pydantic import ValidationError

from ragcore.adapters.config.settings import (
    DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS,
    EmbeddingRuntimeSettings,
)

TIMEOUT_VAR = "EMBEDDING_INGESTION_TIMEOUT"


def _settings() -> EmbeddingRuntimeSettings:
    return EmbeddingRuntimeSettings(_env_file=None)  # type: ignore[call-arg]


def test_sans_variable_le_timeout_vaut_deux_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(TIMEOUT_VAR, raising=False)

    assert _settings().ingestion_timeout == DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS


def test_le_timeout_vient_de_l_environnement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(TIMEOUT_VAR, "30000")

    assert _settings().ingestion_timeout == 30_000


def test_le_timeout_du_backend_ne_s_applique_pas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``EMBEDDING_SERVICE_TIMEOUT`` règle le backend, qui n'embarque qu'une question."""
    monkeypatch.delenv(TIMEOUT_VAR, raising=False)
    monkeypatch.setenv("EMBEDDING_SERVICE_TIMEOUT", "10000")

    assert _settings().ingestion_timeout == DEFAULT_EMBEDDING_INGESTION_TIMEOUT_MS


@pytest.mark.parametrize("value", ["0", "-1", "deux"])
def test_un_timeout_invalide_est_refuse(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(TIMEOUT_VAR, value)

    with pytest.raises(ValidationError, match="ingestion_timeout"):
        _settings()
