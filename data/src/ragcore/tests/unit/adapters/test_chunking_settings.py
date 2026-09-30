"""La découpe, lue de l'environnement à côté du modèle d'embedding."""

import pytest
from pydantic import ValidationError

from ragcore.adapters.config.settings import ChunkingSettings
from ragcore.core.models.processing import ChunkingConfig

MAX_VAR = "CHUNKING_MAX_CHARS"
OVERLAP_VAR = "CHUNKING_OVERLAP_CHARS"
REQUIRED_VARS = {MAX_VAR: "384", OVERLAP_VAR: "25"}


@pytest.fixture(autouse=True)
def _required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED_VARS.items():
        monkeypatch.setenv(name, value)


def _config() -> ChunkingConfig:
    return ChunkingSettings(_env_file=None).to_config()  # type: ignore[call-arg]


def test_la_decoupe_vient_de_l_environnement() -> None:
    assert _config() == ChunkingConfig(max_chars=384, overlap_chars=25)


@pytest.mark.parametrize("name", sorted(REQUIRED_VARS))
def test_une_variable_absente_est_refusee(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.delenv(name)

    with pytest.raises(ValidationError):
        _config()


@pytest.mark.parametrize("name", sorted(REQUIRED_VARS))
@pytest.mark.parametrize("value", ["", "trois", "38.4"])
def test_une_variable_qui_n_est_pas_un_entier_est_refusee(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    """``CHUNKING_MAX_CHARS=`` dans un ``.env`` donne ``''`` : l'absence, pas zéro."""
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        _config()


def test_une_taille_nulle_est_refusee(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MAX_VAR, "0")

    with pytest.raises(ValidationError, match="max_chars"):
        _config()


@pytest.mark.parametrize("overlap_chars", ["384", "400"])
def test_un_recouvrement_qui_n_est_pas_inferieur_a_la_taille_est_refuse(
    monkeypatch: pytest.MonkeyPatch, overlap_chars: str
) -> None:
    """Le curseur de la fenêtre glissante n'avancerait pas : boucle infinie."""
    monkeypatch.setenv(OVERLAP_VAR, overlap_chars)

    with pytest.raises(ValidationError, match="overlap_chars"):
        _config()
