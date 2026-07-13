"""Nœud Kedro : parse documents et détermine l'opération (INSERT vs UPDATE).

Changements post-refonte :
- Rejet des documents invalides → entrée EXCLUDED au manifest
- Suppression de SKIP (plus d'idempotence basée sur hash)
- Tout ce qui parse → INSERT ou UPDATE seulement
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from ragcore.application.run_context import PipelineContext
from ragcore.core.exceptions import ValidationError
from ragcore.core.models.audit import build_event
from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import Operation
from ragcore.core.models.manifest import ManifestEntry
from ragcore.core.ports.manifest_repository import ManifestRepository
from ragcore.core.ports.parser import BaseParser
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.services.exclusion_reasons import (
    REASON_PARSE_ERROR,
    REASON_VALIDATION_ERROR,
)
from ragcore.core.services.idempotence import determine_operation
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED, DOCUMENT_PARSED

logger = logging.getLogger(__name__)


def compute_idempotence_node(  # noqa: PLR0913 — l'identité d'un nœud Kedro EST sa liste d'inputs ; les grouper les cacherait au DAG
    raw_documents: list[RawDocument],
    parser: BaseParser,
    manifest_repo: ManifestRepository,
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
    pipeline_runtime: AsyncRuntime,
) -> tuple[list[tuple[ParsedDocument, Operation]], list[str]]:
    """Parse documents and determine which need processing (INSERT vs UPDATE).

    Les documents rejetés (ValidationError) sont tracés dans le manifest avec
    l'opération EXCLUDED et un message de raison.
    """
    to_process: list[tuple[ParsedDocument, Operation]] = []
    to_skip: list[str] = []

    run_id = pipeline_context.run_id
    owner_id = pipeline_context.owner_id
    source = pipeline_context.source

    for raw in raw_documents:
        try:
            parsed = parser.parse(raw)
        except ValidationError as exc:
            # Rejet de validation — tracer au manifest avec EXCLUDED
            logger.warning("Document invalidé %s — rejeté", raw.source_document_id)
            telemetry.emit(
                build_event(
                    event_type=DOCUMENT_INVALIDATED,
                    run_id=run_id,
                    owner_id=owner_id,
                    source=source,
                    payload={
                        "reason": REASON_VALIDATION_ERROR,
                        "uid": raw.source_document_id,
                        "error": str(exc),
                    },
                    success=False,
                    error_message=str(exc),
                )
            )
            # Écrire une entrée EXCLUDED au manifest
            pipeline_runtime.run(
                manifest_repo.append(
                    ManifestEntry(
                        identifier=None,
                        source_path=raw.source_document_id,
                        owner_id=owner_id,
                        source=source,
                        operation=Operation.EXCLUDED,
                        reason=str(exc),
                        processed_at=datetime.now(UTC),
                    )
                )
            )
            to_skip.append(raw.source_document_id)
            continue
        except Exception as exc:  # noqa: BLE001
            # Autre erreur de parsing
            logger.warning("Erreur parsing document %s — rejeté", raw.source_document_id)
            telemetry.emit(
                build_event(
                    event_type=DOCUMENT_INVALIDATED,
                    run_id=run_id,
                    owner_id=owner_id,
                    source=source,
                    payload={
                        "reason": REASON_PARSE_ERROR,
                        "uid": raw.source_document_id,
                        "error": str(exc),
                    },
                    success=False,
                    error_message=str(exc),
                )
            )
            pipeline_runtime.run(
                manifest_repo.append(
                    ManifestEntry(
                        identifier=None,
                        source_path=raw.source_document_id,
                        owner_id=owner_id,
                        source=source,
                        operation=Operation.EXCLUDED,
                        reason=f"{REASON_PARSE_ERROR}: {exc}",
                        processed_at=datetime.now(UTC),
                    )
                )
            )
            to_skip.append(raw.source_document_id)
            continue

        # Document valide — détermine l'opération (INSERT ou UPDATE)
        manifest_entry = pipeline_runtime.run(
            manifest_repo.last_for_identifier(parsed.identifier, parsed.owner_id)
        )
        operation = determine_operation(manifest_entry)

        telemetry.emit(
            build_event(
                event_type=DOCUMENT_PARSED,
                run_id=run_id,
                owner_id=owner_id,
                source=source,
                document_id=parsed.identifier.serialize(),
                payload={"operation": operation.value},
            )
        )

        to_process.append((parsed, operation))

    return to_process, to_skip
