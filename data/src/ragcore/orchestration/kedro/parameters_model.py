"""La forme de ``parameters.yml``, validée en tête de run.

Une clé inconnue, absente ou mal typée arrête le run, toutes les erreurs listées
ensemble. Strict : ``"false"`` n'est pas un booléen.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import ErrorDetails

__all__ = [
    "DevParameters",
    "RunParameters",
    "validate_parameters",
]

_MISSING_ERROR_TYPE = "missing"
_SOURCE_KEY = "source"
_DEV_FIELD = "dev"


class _StrictParameters(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class DevParameters(_StrictParameters):
    """Validé partout, même là où les valeurs sûres le remplacent."""

    nuke_all: bool
    embedding_enabled: bool
    skip_unconfigured: bool
    include_path: bool
    """Écrits dans Mongo et Neo4j."""
    include_content_neo4j: bool
    """Sous ``_text_content``."""


class RunParameters(_StrictParameters):
    """``parameters.yml`` plus les ``--params``, que Kedro fusionne à la racine.
    ``source`` vaut aussi en prod : elle est rangée à part, le reste sous ``dev``."""

    dev: DevParameters
    source: str | None = None
    """``None`` : le run prend ``SOURCE`` de l'environnement."""


def validate_parameters(params: dict[str, Any]) -> RunParameters:
    dev_params = {key: value for key, value in params.items() if key != _SOURCE_KEY}
    run_params = {_DEV_FIELD: dev_params}
    if _SOURCE_KEY in params:
        run_params[_SOURCE_KEY] = params[_SOURCE_KEY]
    try:
        return RunParameters.model_validate(run_params)
    except ValidationError as exc:
        details = "\n".join(_describe(error) for error in exc.errors())
        raise ValueError(
            f"`parameters.yml` invalide : le run est interrompu.\n{details}"
        ) from exc


def _describe(error: ErrorDetails) -> str:
    """Au chemin du fichier : ``dev`` est une rangée du modèle, pas une clé."""
    loc = error["loc"]
    if loc[:1] == (_DEV_FIELD,):
        loc = loc[1:]
    path = ".".join(str(part) for part in loc)
    line = f"- `{path}` : {error['msg']}"
    if error["type"] == _MISSING_ERROR_TYPE:
        return line
    return f"{line} (reçu : {error['input']!r})"
