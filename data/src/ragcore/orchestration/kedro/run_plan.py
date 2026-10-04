"""Le plan du run : ce qu'il écrit, et comment, dérivé une seule fois des paramètres et
de l'environnement. L'assemblage le lit sans jamais le re-dériver.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ragcore.adapters.config.settings import Environment, InfraSettings
from ragcore.adapters.storage.neo4j.node_properties import NodeHydration
from ragcore.core.models.enums import SourceName
from ragcore.core.models.processing import ChunkingConfig
from ragcore.orchestration.kedro.parameters_model import (
    DevParameters,
    validate_parameters,
)
from ragcore.orchestration.kedro.run_parameters import (
    DEV_ENVIRONMENT,
    resolve_dev_settings,
    resolve_sources,
)

__all__ = ["RunPlan", "plan_run"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunPlan:
    chunking: ChunkingConfig
    index: str
    sources: tuple[SourceName, ...]
    include_path: bool
    """Les chemins des fichiers source dans les documents Mongo. ``False`` hors ``dev``."""
    node_hydration: NodeHydration
    """Partagée entre le dépôt du hook et ceux des workers (ADR-011)."""
    embedding_enabled: bool
    """ADR-012. ``True`` hors ``dev``."""
    skip_unconfigured: bool
    """``True`` retire les métadonnées non configurées (ADR-011). ``True`` hors ``dev``."""
    nuke_all: bool
    """``False`` hors ``dev``."""


def plan_run(
    params: dict[str, Any], settings: InfraSettings, chunking: ChunkingConfig
) -> RunPlan:
    """Sans I/O : un ``parameters.yml`` invalide ou une source inconnue échoue ici,
    avant qu'aucun client ne soit ouvert. ``params`` inclut déjà les ``--params``.
    """
    parameters = validate_parameters(params)
    is_dev = settings.environment == DEV_ENVIRONMENT
    dev = resolve_dev_settings(parameters.dev, settings.environment)
    requested_source = (
        settings.source if parameters.source is None else parameters.source
    )
    plan = RunPlan(
        chunking=chunking,
        index=settings.opensearch_index,
        sources=resolve_sources(requested_source),
        include_path=dev.include_path,
        node_hydration=_node_hydration(dev, is_dev),
        embedding_enabled=dev.embedding_enabled,
        skip_unconfigured=dev.skip_unconfigured,
        nuke_all=dev.nuke_all,
    )
    if not is_dev:
        _warn_dev_ignored(settings.environment)
    _log_plan(plan)
    return plan


def _node_hydration(dev: DevParameters, is_dev: bool) -> NodeHydration:
    """Hors ``dev``, pas de métadonnées sur le nœud (ADR-011)."""
    return NodeHydration(
        metadata=is_dev,
        include_path=dev.include_path,
        include_content=dev.include_content_neo4j,
    )


def _warn_dev_ignored(environment: Environment) -> None:
    logger.warning(
        "ENVIRONMENT=%s : parameters.yml est ignoré. Rien n'est "
        "effacé, l'embedding est calculé, les métadonnées des balises non configurées "
        "sont retirées, aucun chemin de fichier n'est écrit et les nœuds Neo4j restent "
        "maigres.",
        environment,
    )


def _log_plan(plan: RunPlan) -> None:
    logger.info("Index OpenSearch : %s", plan.index)
    logger.info(
        "Découpe : %d caractères, recouvrement %d",
        plan.chunking.max_chars,
        plan.chunking.overlap_chars,
    )
    logger.info(
        "Sources du run (%d) : %s",
        len(plan.sources),
        ", ".join(s.value for s in plan.sources),
    )
    logger.info(
        "Balises non configurées : %s",
        "métadonnées retirées" if plan.skip_unconfigured else "métadonnées ingérées",
    )
    if not plan.embedding_enabled:
        logger.warning(
            "EMBEDDING COUPÉ (dev, ADR-012) : aucun vecteur ne sera calculé. Les "
            "passages sont écrits dans l'index %s sans vecteur : seule la recherche "
            "lexicale les trouvera. Mongo et Neo4j sont peuplés normalement.",
            plan.index,
        )
