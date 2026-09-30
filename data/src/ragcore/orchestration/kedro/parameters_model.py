"""La forme de ``parameters.yml`` : un modèle strict, validé une fois en tête de run.

C'est le seul endroit du dépôt qui connaisse la forme du YAML. Une clé inconnue,
absente ou mal typée arrête le run avant tout nœud, et toutes les erreurs sont listées
ensemble. Strict veut dire sans conversion : ``"false"`` n'est pas un booléen, ``"384"``
n'est pas un entier.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import ErrorDetails

from ragcore.core.models.processing import ChunkingConfig, EmbeddingConfig

__all__ = [
    "EmbeddingRuntimeParameters",
    "ExportationParameters",
    "IngestionParameters",
    "MaintenanceParameters",
    "Neo4jParameters",
    "NodeLabelsParameters",
    "validate_parameters",
]

_MISSING_ERROR_TYPE = "missing"


class _StrictParameters(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class EmbeddingRuntimeParameters(_StrictParameters):
    """L'interrupteur d'embedding (ADR-023), arbitré ensuite par l'environnement."""

    enabled: bool


class NodeLabelsParameters(_StrictParameters):
    """Le label d'un nœud Neo4j d'après les 8 lettres de son identifiant."""

    default: str
    by_prefix: dict[str, str]


class Neo4jParameters(_StrictParameters):
    """L'hydratation des nœuds (ADR-022 §2) et leurs labels."""

    include_path: bool
    include_content: bool
    labels: NodeLabelsParameters


class ExportationParameters(_StrictParameters):
    """Le sort des balises non configurées (ADR-022 §1) et les nœuds Neo4j."""

    skip_unconfigured: bool
    neo4j: Neo4jParameters


class MaintenanceParameters(_StrictParameters):
    """L'effacement de toutes les bases en tête de run, refusé hors ``dev``."""

    nuke_all: bool


class IngestionParameters(_StrictParameters):
    """Tout ``parameters.yml``, plus les ``--params`` de la ligne de commande."""

    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    embedding_runtime: EmbeddingRuntimeParameters
    exportation: ExportationParameters
    maintenance: MaintenanceParameters
    source: str | None = None
    """``--params source=cass``. Kedro fusionne les ``--params`` dans les paramètres :
    ils arrivent ici avec le YAML, et une faute (``sorce=cass``) est une clé inconnue.
    ``None`` : pas de ``--params source``, le run prend ``SOURCE`` du ``.env``."""


def validate_parameters(params: dict[str, Any]) -> IngestionParameters:
    """Les paramètres du run, typés — ou un ARRÊT qui liste toutes les erreurs."""
    try:
        return IngestionParameters.model_validate(params)
    except ValidationError as exc:
        details = "\n".join(_describe(error) for error in exc.errors())
        raise ValueError(
            f"`parameters.yml` invalide : le run est interrompu.\n{details}"
        ) from exc


def _describe(error: ErrorDetails) -> str:
    path = ".".join(str(part) for part in error["loc"])
    line = f"- `{path}` : {error['msg']}"
    if error["type"] == _MISSING_ERROR_TYPE:
        return line
    return f"{line} (reçu : {error['input']!r})"
