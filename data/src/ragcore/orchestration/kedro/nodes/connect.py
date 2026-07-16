from __future__ import annotations

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.document import RawDocument
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import DOCUMENT_FETCHED, DOCUMENT_SKIPPED


def connect_node(
    connector: BaseConnector,
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
    pipeline_runtime: AsyncRuntime,
    nuke_done: dict[str, bool],
) -> list[RawDocument]:
    """Fetch all raw documents from the source connector."""
    del nuke_done  # signal-only input: ensures nukeAll runs before connect

    async def _fetch() -> list[RawDocument]:
        return [doc async for doc in connector.fetch_all(pipeline_context.owner_id)]

    # Le pont sync→async passe par le runtime du hook (sa boucle), jamais une globale
    # (§11 : ``_async_utils.run_async`` tenait une boucle unique, point de
    # sérialisation que le port ``AsyncRuntime`` supprime par construction).
    documents = pipeline_runtime.run(_fetch())

    telemetry.emit(
        build_event(
            event_type=DOCUMENT_FETCHED,
            run_id=pipeline_context.run_id,
            owner_id=pipeline_context.owner_id,
            source=pipeline_context.source,
            payload={"count": len(documents)},
        )
    )

    # Ce que le connecteur a écarté (artefacts d'export, fichiers illisibles) n'entre
    # PAS dans `document.fetched` — donc pas dans `seen`, donc invisible à l'équation
    # de complétude. Sans cette boucle, le compte que le connecteur tient si
    # soigneusement s'évaporait ici. Un `document.skipped` par raison, HORS équation :
    # le bilan dit « N écartés, dont X illisibles » sans fausser le dénominateur.
    for reason, count in connector.skipped.items():
        telemetry.emit(
            build_event(
                event_type=DOCUMENT_SKIPPED,
                run_id=pipeline_context.run_id,
                owner_id=pipeline_context.owner_id,
                source=pipeline_context.source,
                payload={"reason": reason, "count": count},
            )
        )
    return documents
