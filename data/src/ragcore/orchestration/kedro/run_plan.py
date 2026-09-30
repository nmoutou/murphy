"""Le plan du run : ce qu'il écrit, et comment — dérivé UNE fois, en tête de run.

Tout ce que le hook déduit des paramètres (``parameters.yml``, ``--params``) et de
l'environnement (dont la découpe, ``ChunkingSettings``) est rassemblé ici, en une donnée
figée. Les briques de l'assemblage (``stores``, ``assembly``) la lisent ; aucune ne
re-dérive ce qu'elle contient — deux dérivations sont deux occasions de diverger.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ragcore.adapters.config.settings import Environment, InfraSettings
from ragcore.adapters.storage.neo4j.node_properties import NodeHydration, NodeLabels
from ragcore.core.models.enums import SourceName
from ragcore.core.models.processing import ChunkingConfig
from ragcore.orchestration.kedro.parameters_model import (
    NodeHydrationParameters,
    validate_parameters,
)
from ragcore.orchestration.kedro.run_parameters import (
    DEV_ENVIRONMENT,
    resolve_dev_settings,
    resolve_sources,
)
from ragcore.sources.registry import node_labels_by_prefix

__all__ = ["RunPlan", "plan_run"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunPlan:
    """Ce que ce run écrit, et comment."""

    chunking: ChunkingConfig
    """La découpe : ``CHUNKING_MAX_CHARS`` et ``CHUNKING_OVERLAP_CHARS``."""
    collection: str
    """La collection Qdrant : un nom fixe, lu de ``QDRANT_COLLECTION``."""
    sources: tuple[SourceName, ...]
    node_hydration: NodeHydration
    """L'hydratation des nœuds Neo4j (ADR-022 §2) : résolue UNE fois, partagée entre le
    dépôt du hook et ceux des workers — deux résolutions seraient deux occasions de
    diverger."""
    node_labels: NodeLabels
    """Le label des nœuds Neo4j d'après le préfixe de l'identifiant, déclaré par les
    sources."""
    embedding_enabled: bool
    """L'interrupteur d'embedding (ADR-023) : toujours ``True`` hors ``dev``."""
    skip_unconfigured: bool
    """Le curseur des balises non configurées : ``True`` retire leurs métadonnées du
    document. Toujours ``True`` hors ``dev`` (ADR-022 §1)."""
    nuke_all: bool
    """L'effacement de toutes les bases en tête de run : toujours ``False`` hors
    ``dev``."""

    @property
    def context_source(self) -> SourceName | None:
        """La source du contexte de run : la sienne si le run est mono-source.

        ``None`` signifie « ce run n'est pas mono-source ». Le modèle le prévoyait déjà
        (``SourceName | None``) : la porte était ouverte, on ne force rien. Un run
        mono-source garde SA source dans le contexte — les événements qu'il émet restent
        donc attribuables exactement comme avant.
        """
        return self.sources[0] if len(self.sources) == 1 else None


def plan_run(
    params: dict[str, Any], settings: InfraSettings, chunking: ChunkingConfig
) -> RunPlan:
    """Dérive le plan du run. Sans I/O : rien n'est ouvert, seul le plan est journalisé.

    ``params`` contient déjà les ``--params`` de la ligne de commande : Kedro les
    fusionne dans les paramètres. Un ``parameters.yml`` invalide ou une source inconnue
    (``--params source=cas``) échoue ici, avant qu'aucun client ne soit ouvert. Hors
    ``dev``, le bloc ``dev`` est remplacé par les valeurs sûres, et un avertissement le
    signale.
    """
    parameters = validate_parameters(params)
    is_dev = settings.environment == DEV_ENVIRONMENT
    dev = resolve_dev_settings(parameters.dev, settings.environment)
    # Un run nu ingère TOUTES les sources ; `--params source=cass` le restreint.
    #
    # ⚠️ DETTE OUVERTE : un run qui mélange des sources doit pouvoir dire *laquelle* a
    # échoué, et il ne le peut pas encore. `RunStats.breakdowns` ne ventile que `reason`
    # et `operation` (cf. `adapters/telemetry/aggregator.py`), PAS la source. La
    # restriction garde la voie du rejeu ciblé ouverte, mais le bilan ne dit pas encore
    # *quoi* rejouer.
    requested_source = (
        settings.source if parameters.source is None else parameters.source
    )
    plan = RunPlan(
        chunking=chunking,
        collection=settings.qdrant_collection,
        sources=resolve_sources(requested_source),
        node_hydration=_node_hydration(dev.node_hydration, is_dev),
        node_labels=NodeLabels(by_prefix=node_labels_by_prefix()),
        embedding_enabled=dev.embedding_enabled,
        skip_unconfigured=dev.skip_unconfigured,
        nuke_all=dev.nuke_all,
    )
    if not is_dev:
        _warn_dev_ignored(settings.environment)
    _log_plan(plan)
    return plan


def _node_hydration(hydration: NodeHydrationParameters, is_dev: bool) -> NodeHydration:
    """Hors ``dev``, le nœud est maigre : ``NodeHydration()`` (ADR-022 §2)."""
    return NodeHydration(
        metadata=is_dev,
        include_path=hydration.include_path,
        include_content=hydration.include_content,
    )


def _warn_dev_ignored(environment: Environment) -> None:
    logger.warning(
        "ENVIRONMENT=%s : le bloc `dev` de parameters.yml est ignoré. Rien n'est "
        "effacé, l'embedding est calculé, les métadonnées des balises non configurées "
        "sont retirées et les nœuds Neo4j restent maigres.",
        environment,
    )


def _log_plan(plan: RunPlan) -> None:
    logger.info("Collection Qdrant : %s", plan.collection)
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
        # En dehors de `dev`, on embarque TOUJOURS, quoi que dise le flag : un flag
        # oublié à `false` ne doit pas pouvoir produire une collection vide en prod.
        logger.warning(
            "EMBEDDING COUPÉ (dev, ADR-023) : aucun vecteur ne sera calculé ni écrit "
            "dans Qdrant. Mongo et Neo4j sont peuplés normalement — régime d'itération "
            "sur le modèle de données. La collection %s restera vide pour ce run.",
            plan.collection,
        )
