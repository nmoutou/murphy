"""Valeurs validées + ``ENVIRONMENT`` → réglages effectifs du run."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kedro.io import DataCatalog, DatasetError

from ragcore.adapters.config.settings import Environment
from ragcore.core.models.enums import SourceName
from ragcore.orchestration.kedro.parameters_model import DevParameters
from ragcore.sources.registry import all_sources

__all__ = [
    "DEV_ENVIRONMENT",
    "SAFE_DEV_SETTINGS",
    "load_parameters",
    "resolve_dev_settings",
    "resolve_sources",
]

DEV_ENVIRONMENT: Environment = "dev"
"""Seule valeur qui applique ``parameters.yml``."""

SAFE_DEV_SETTINGS = DevParameters(
    nuke_all=False,
    embedding_enabled=True,
    skip_unconfigured=True,
    include_path=False,
    include_content_neo4j=False,
)
"""``parameters.yml`` tel qu'il s'applique hors ``dev``."""


def load_parameters(catalog: DataCatalog) -> dict[str, Any]:
    """Arrête le run si le fichier est illisible : pas de repli silencieux vers ``{}``.
    Seule la ``DatasetError`` de Kedro est traduite ; toute autre exception remonte.
    """
    try:
        params: dict[str, Any] = catalog.load("parameters")
    except DatasetError as exc:
        raise RuntimeError(
            "Impossible de charger `parameters.yml` : le run est interrompu. Il n'y a "
            "pas de réglages de dev par défaut."
        ) from exc
    return params


def resolve_dev_settings(dev: DevParameters, environment: Environment) -> DevParameters:
    """Le YAML en ``dev``, les valeurs sûres ailleurs : un ``parameters.yml`` traîné en
    prod ne doit jamais effacer une base ni couper l'embedding."""
    return dev if environment == DEV_ENVIRONMENT else SAFE_DEV_SETTINGS


def resolve_sources(
    value: str | SourceName | Iterable[str] | None,
) -> tuple[SourceName, ...]:
    """Accepte rien ou ``"all"`` (toutes), ``"cass"``, ``"cass,jade"`` ou une liste.

    Une source inconnue lève au démarrage, même au milieu d'une liste : ignorée, elle
    donnerait un run silencieusement incomplet.
    """
    if value is None:
        return all_sources()

    if isinstance(value, SourceName):
        return (value,)

    if isinstance(value, str):
        if value.strip().lower() in {"", "all", "*"}:
            return all_sources()
        names: list[str] = [part.strip() for part in value.split(",") if part.strip()]
    else:
        names = [str(part).strip() for part in value]

    if not names:
        return all_sources()

    resolved: list[SourceName] = []
    for name in names:
        try:
            source = SourceName(name.lower())
        except ValueError as exc:
            connues = ", ".join(s.value for s in all_sources())
            msg = f"Source inconnue : {name!r}. Sources ingérables : {connues}."
            raise ValueError(msg) from exc
        if source not in resolved:
            resolved.append(source)

    return tuple(resolved)
