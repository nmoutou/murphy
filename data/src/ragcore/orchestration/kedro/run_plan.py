"""Le plan du run : ce qu'il écrit, et comment — dérivé UNE fois, en tête de run.

Tout ce que le hook déduit des paramètres (``parameters.yml``, ``--params``) et de
l'environnement est rassemblé ici, en une donnée figée. Les briques de l'assemblage
(``stores``, ``assembly``) la lisent ; aucune ne re-dérive ce qu'elle contient — deux
dérivations sont deux occasions de diverger.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ragcore.adapters.config.settings import InfraSettings
from ragcore.adapters.storage.neo4j.node_properties import NodeHydration, NodeLabels
from ragcore.core.models.enums import SourceName
from ragcore.core.models.processing import ChunkingConfig, EmbeddingConfig
from ragcore.orchestration.kedro.run_parameters import (
    resolve_chunking,
    resolve_embedding_enabled,
    resolve_embedding_model,
    resolve_node_hydration,
    resolve_node_labels,
    resolve_sources,
)

__all__ = ["RunPlan", "plan_run"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunPlan:
    """Ce que ce run écrit, et comment."""

    chunking: ChunkingConfig
    embedding: EmbeddingConfig
    collection: str
    """La collection Qdrant : un nom fixe, lu de ``QDRANT_COLLECTION``."""
    sources: tuple[SourceName, ...]
    node_hydration: NodeHydration
    """L'hydratation des nœuds Neo4j (ADR-022 §2) : résolue UNE fois, partagée entre le
    dépôt du hook et ceux des workers — deux résolutions seraient deux occasions de
    diverger."""
    node_labels: NodeLabels
    """Le label des nœuds Neo4j d'après le préfixe de l'identifiant, lu dans le YAML."""
    embedding_enabled: bool
    """L'interrupteur d'embedding (dev, ADR-023), arbitré par l'environnement."""

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
    params: dict[str, Any], settings: InfraSettings, run_params: dict[str, Any]
) -> RunPlan:
    """Dérive le plan du run. Sans I/O : rien n'est ouvert, seul le plan est journalisé.

    Une source inconnue (``--params source=cas``) ou un réglage manquant échoue ici,
    avant qu'aucun client ne soit ouvert.
    """
    # Les `--params` de la ligne de commande. Kedro 1.x les passe sous
    # `runtime_params` ; l'ancienne clé `extra_params` n'existe plus, et la lire
    # faisait ignorer `--params source=…` en silence.
    extra = run_params.get("runtime_params") or {}

    plan = RunPlan(
        chunking=resolve_chunking(params),
        embedding=resolve_embedding_model(params),
        collection=settings.qdrant_collection,
        # Les SOURCES du run. Un run nu les ingère TOUTES ; `--params source=cass` ou
        # `source=cass,jade` le restreint.
        #
        # ⚠️ DETTE OUVERTE : un run qui mélange des sources doit pouvoir dire *laquelle*
        # a échoué, et il ne le peut pas encore. `RunStats.breakdowns` ne ventile que
        # `reason` et `operation` (cf. `adapters/telemetry/aggregator.py`), PAS la source.
        # La restriction par paramètre garde la voie du rejeu ciblé ouverte, mais le
        # bilan ne dit pas encore *quoi* rejouer.
        sources=resolve_sources(extra.get("source", settings.source)),
        node_hydration=resolve_node_hydration(params, settings.environment),
        node_labels=resolve_node_labels(params),
        embedding_enabled=resolve_embedding_enabled(params, settings.environment),
    )
    _log_plan(plan)
    return plan


def _log_plan(plan: RunPlan) -> None:
    logger.info("Collection Qdrant : %s", plan.collection)
    logger.info(
        "Sources du run (%d) : %s",
        len(plan.sources),
        ", ".join(s.value for s in plan.sources),
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
