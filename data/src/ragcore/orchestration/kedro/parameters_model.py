"""La forme de ``parameters.yml`` : un modèle strict, validé une fois en tête de run.

C'est le seul endroit du dépôt qui connaisse la forme du YAML. Une clé inconnue,
absente ou mal typée arrête le run avant tout nœud, et toutes les erreurs sont listées
ensemble, chacune par son chemin dans le fichier. Strict veut dire sans conversion :
``"false"`` n'est pas un booléen.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import ErrorDetails

__all__ = [
    "DevParameters",
    "NodeHydrationParameters",
    "RunParameters",
    "validate_parameters",
]

_MISSING_ERROR_TYPE = "missing"
_SOURCE_KEY = "source"
_DEV_FIELD = "dev"


class _StrictParameters(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class NodeHydrationParameters(_StrictParameters):
    """Ce que les nœuds Neo4j portent en plus en dev (ADR-022 §2)."""

    include_path: bool
    include_content: bool


class DevParameters(_StrictParameters):
    """Tout ``parameters.yml`` : des commodités de dev. Hors ``dev``, le fichier entier
    est remplacé par les valeurs sûres (``run_parameters.resolve_dev_settings``) ; il
    est validé partout."""

    nuke_all: bool
    embedding_enabled: bool
    skip_unconfigured: bool
    node_hydration: NodeHydrationParameters


class RunParameters(_StrictParameters):
    """``parameters.yml`` plus les ``--params`` de la ligne de commande.

    Kedro fusionne les ``--params`` à la racine, avec les clés du fichier. ``source``
    n'est pas une commodité de dev : elle vaut en prod aussi, donc elle est rangée à
    part, et le reste passe sous ``dev`` (``validate_parameters``). Une faute
    (``sorce=cass``) est une clé inconnue du fichier."""

    dev: DevParameters
    source: str | None = None
    """``--params source=cass``. ``None`` : pas de ``--params source``, le run prend
    ``SOURCE`` du ``.env``."""


def validate_parameters(params: dict[str, Any]) -> RunParameters:
    """Les paramètres du run, typés — ou un ARRÊT qui liste toutes les erreurs."""
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
    """L'erreur au chemin du fichier : ``dev`` est une rangée du modèle, pas une clé."""
    loc = error["loc"]
    if loc[:1] == (_DEV_FIELD,):
        loc = loc[1:]
    path = ".".join(str(part) for part in loc)
    line = f"- `{path}` : {error['msg']}"
    if error["type"] == _MISSING_ERROR_TYPE:
        return line
    return f"{line} (reçu : {error['input']!r})"
