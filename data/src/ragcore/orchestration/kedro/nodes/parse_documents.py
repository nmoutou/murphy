"""Parse les documents : ceux qui parsent partent à l'ingestion, déjà en base ou non ;
les autres sont rejetés et comptés (``document.invalidated``).

Les collisions (ADR-025) sont comptées par (document, clé), document refusé compris.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from ragcore.application.run_context import PipelineContext
from ragcore.core.exceptions import CollisionError, ParseError, ValidationError
from ragcore.core.models.audit import build_event
from ragcore.core.models.collision import Collision
from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.unknown_tally import UnknownExample
from ragcore.core.ports.parser import BaseParser, ParseResult
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.services.exclusion_reasons import (
    REASON_COLLISION,
    REASON_PARSE_ERROR,
    REASON_VALIDATION_ERROR,
)
from ragcore.core.services.unknown_categories import (
    CATEGORY_LINK,
    CATEGORY_ROOT,
    CATEGORY_TAG,
)
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED, DOCUMENT_PARSED

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Rejection:
    reason: str
    log_message: str


_VALIDATION_REJECTION = _Rejection(
    REASON_VALIDATION_ERROR, "Document invalidé %s — rejeté"
)
_PARSE_REJECTION = _Rejection(REASON_PARSE_ERROR, "Erreur parsing document %s — rejeté")
_COLLISION_REJECTION = _Rejection(
    REASON_COLLISION, "Collision non configurée dans le document %s — rejeté"
)


def parse_documents_node(
    raw_documents: list[RawDocument],
    parser: BaseParser,
    pipeline_context: PipelineContext,
    # WorkerTelemetry, pas TelemetryPort : ce nœud déclare aussi (`record_unknown`)
    telemetry: WorkerTelemetry,
    skip_unconfigured: bool,
) -> tuple[list[ParsedDocument], list[str]]:
    """Le site de parse : déclare toujours les signaux non configurés (``tags``,
    ``links``, ``roots``), puis applique ``skip_unconfigured``, qui retire les
    métadonnées non configurées. Les liens non configurés sont retirés à l'extraction.
    """
    site = _ParseSite(pipeline_context, telemetry)
    to_process: list[ParsedDocument] = []
    to_skip: list[str] = []

    for raw in raw_documents:
        result = _parse(raw, parser, site)
        if result is None:
            to_skip.append(raw.source_document_id)
            continue
        site.declare_signals(result)
        site.declare_collisions(result.collisions)
        parsed = _apply_cursor(result, skip_unconfigured)
        site.declare_parsed(raw, parsed)
        to_process.append(parsed)

    return to_process, to_skip


def _parse(
    raw: RawDocument, parser: BaseParser, site: _ParseSite
) -> ParseResult | None:
    """``None`` pour un document rejeté, déjà tracé."""
    try:
        return parser.parse(raw)
    except CollisionError as exc:
        site.declare_collisions(exc.collisions)
        site.exclude(raw, exc, _COLLISION_REJECTION)
    except ValidationError as exc:
        site.exclude(raw, exc, _VALIDATION_REJECTION)
    except ParseError as exc:
        # Toute autre exception sort du contrat de BaseParser : un bug, qui arrête le run
        site.exclude(raw, exc, _PARSE_REJECTION)
    return None


def _apply_cursor(result: ParseResult, skip_unconfigured: bool) -> ParsedDocument:
    """Retire les métadonnées non configurées. `ParsedDocument` est figé : on le
    reconstruit."""
    parsed = result.document
    if not skip_unconfigured or not result.unconfigured_tags:
        return parsed
    return parsed.model_copy(
        update={
            "metadata": {
                key: value
                for key, value in parsed.metadata.items()
                if key not in result.unconfigured_tags
            }
        }
    )


@dataclass(frozen=True)
class _ParseSite:
    """Trace un rejet, un signal ou un document parsé.

    La source vient de `raw.source`, jamais du contexte : en run multi-source,
    `context.source` vaut None.
    """

    context: PipelineContext
    telemetry: WorkerTelemetry

    def exclude(self, raw: RawDocument, exc: Exception, rejection: _Rejection) -> None:
        logger.warning(rejection.log_message, raw.source_document_id)
        self.telemetry.emit(
            build_event(
                event_type=DOCUMENT_INVALIDATED,
                run_id=self.context.run_id,
                source=raw.source,
                payload={
                    "reason": rejection.reason,
                    "uid": raw.source_document_id,
                    "error": str(exc),
                },
                success=False,
                error_message=str(exc),
            )
        )

    def declare_signals(self, result: ParseResult) -> None:
        """Toujours, et avant le curseur : `skip` n'efface jamais le signal."""
        identifier = result.document.identifier.serialize()
        signals = {
            CATEGORY_TAG: result.unconfigured_tags,
            CATEGORY_LINK: result.unconfigured_links,
            CATEGORY_ROOT: result.unknown_roots,
        }
        for category, values in signals.items():
            for value, source_file in values.items():
                example = UnknownExample(identifier=identifier, source_file=source_file)
                self.telemetry.record_unknown(category, value, example)

    def declare_parsed(self, raw: RawDocument, parsed: ParsedDocument) -> None:
        self.telemetry.emit(
            build_event(
                event_type=DOCUMENT_PARSED,
                run_id=self.context.run_id,
                source=raw.source,
                document_id=parsed.identifier.serialize(),
            )
        )

    def declare_collisions(self, collisions: Sequence[Collision]) -> None:
        """Une par (document, clé)."""
        for collision in collisions:
            self.telemetry.record_collision(collision.key, collision.source_files())
