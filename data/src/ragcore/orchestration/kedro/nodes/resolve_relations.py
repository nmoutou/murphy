"""Nœud de la phase 2 : il consomme l'``IngestionOutcome``, donc ne tourne qu'une fois
tous les nœuds du run écrits.

Non parallélisé : il traite l'union en un batch, sur le runtime du hook.
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
    return pipeline_runtime.run(
        resolve_service.execute(
            ingestion_outcome.relations,
            ingestion_outcome.written_node_ids,
            pipeline_context,
        )
    )
