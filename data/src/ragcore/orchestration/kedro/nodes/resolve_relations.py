"""Nœud phase 2 — les arêtes, après la barrière.

Ce nœud consomme l'``IngestionOutcome`` de la phase 1 : c'est cette dépendance de
données qui EST la barrière. Kedro ne peut pas l'ordonnancer avant que tous les nœuds
du run existent, donc ``ResolveRelationsService`` peut faire ses ``MATCH`` sans risque
qu'une cible manque parce qu'elle n'est pas encore écrite (le reste — les cibles
réellement absentes du corpus — part au registre des pendantes, §13).

Le service est async ; le pont sync→async est le ``pipeline_runtime`` du hook (sa
boucle, ses clients). Ce nœud n'est PAS parallélisé : il traite l'union en un batch,
pas document par document. Il n'a donc pas besoin du pool.
"""

from __future__ import annotations

from ragcore.application.ingestion_runner import IngestionOutcome
from ragcore.application.resolve_relations import (
    ResolutionOutcome,
    ResolveRelationsService,
)
from ragcore.application.run_context import PipelineContext
from ragcore.core.ports.runtime import AsyncRuntime

__all__ = ["resolve_relations_node"]


def resolve_relations_node(
    ingestion_outcome: IngestionOutcome,
    resolve_service: ResolveRelationsService,
    pipeline_runtime: AsyncRuntime,
    pipeline_context: PipelineContext,
) -> ResolutionOutcome:
    """Réduit puis écrit les arêtes du run, et promeut les pendantes résolues."""
    return pipeline_runtime.run(
        resolve_service.execute(
            ingestion_outcome.relations,
            ingestion_outcome.written_node_ids,
            pipeline_context,
        )
    )
