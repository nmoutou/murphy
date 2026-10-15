"""Parse un flux de documents : ceux qui parsent partent à l'ingestion, déjà en base ou
non ; les autres sont rejetés et comptés (``document.invalidated``).

Les collisions sont déclarées par (document, clé), document refusé compris.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from time import perf_counter

from ragcore.core.exceptions import (
    CollisionError,
    FacetRootCollisionError,
    ParseError,
    ValidationError,
)
from ragcore.core.models.audit import build_event
from ragcore.core.models.collision import Collision
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.problems import InvalidatedDocument
from ragcore.core.models.unknown_tally import UnknownExample
from ragcore.core.ports.parser import BaseParser, ParseResult
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.services.collision_reasons import (
    COLLISION_FACET_ROOT_DUPLICATED,
    COLLISION_METADATA,
)
from ragcore.core.services.exclusion_reasons import REASON_PARSE_ERROR
from ragcore.core.services.unknown_categories import (
    CATEGORY_LINK,
    CATEGORY_ROOT,
    CATEGORY_TAG,
)
from ragcore.core.statistics_measures import (
    STEP_PARSE,
    milliseconds_since,
    step_measure,
)
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED, DOCUMENT_PARSED

from .run_context import PipelineContext

__all__ = ["DocumentParsing"]

logger = logging.getLogger(__name__)


class DocumentParsing:
    """Le site de parse : déclare toujours les signaux non configurés (``tags``,
    ``links``, ``roots``), puis applique ``skip_unconfigured``, qui retire les
    métadonnées non configurées. Les liens non configurés sont retirés à l'extraction.

    ``telemetry`` est une ``WorkerTelemetry`` : le parse déclare aussi des inconnus
    (``record_unknown``).
    """

    def __init__(
        self,
        parser: BaseParser,
        context: PipelineContext,
        telemetry: WorkerTelemetry,
        skip_unconfigured: bool,
    ) -> None:
        self._parser = parser
        self._site = _ParseSite(context, telemetry)
        self._skip_unconfigured = skip_unconfigured
        self.skipped: list[str] = []
        """Les documents rejetés, complet une fois le flux épuisé."""

    def parse_all(
        self, raw_documents: Iterable[RawDocument]
    ) -> Iterator[ParsedDocument]:
        for raw in raw_documents:
            result = _timed_parse(raw, self._parser, self._site)
            if result is None:
                self.skipped.append(raw.source_document_id)
                continue
            self._site.declare_signals(result)
            self._site.declare_collisions(_metadata_records(result.collisions))
            parsed = _apply_cursor(result, self._skip_unconfigured)
            self._site.declare_parsed(raw, parsed)
            yield parsed


def _timed_parse(
    raw: RawDocument, parser: BaseParser, site: _ParseSite
) -> ParseResult | None:
    started = perf_counter()
    result = _parse(raw, parser, site)
    site.telemetry.record_measure(
        step_measure(raw.source, STEP_PARSE),
        milliseconds_since(started),
        raw.source_document_id,
    )
    return result


def _parse(
    raw: RawDocument, parser: BaseParser, site: _ParseSite
) -> ParseResult | None:
    """``None`` pour un document rejeté, déjà tracé."""
    try:
        return parser.parse(raw)
    except CollisionError as exc:
        site.declare_collisions(_metadata_records(exc.collisions))
        site.exclude(raw, exc, exc.reason)
    except FacetRootCollisionError as exc:
        site.declare_collisions(_facet_root_records(raw, exc))
        site.exclude(raw, exc, exc.reason)
    except ValidationError as exc:
        site.exclude(raw, exc, exc.reason)
    except ParseError as exc:
        # Toute autre exception sort du contrat de BaseParser : un bug, qui arrête le run
        site.exclude(raw, exc, REASON_PARSE_ERROR)
    return None


def _metadata_records(collisions: Sequence[Collision]) -> list[CollisionRecord]:
    return [
        CollisionRecord(
            source=collision.source,
            reason=COLLISION_METADATA,
            identifier=collision.identifier,
            key=collision.key,
            files=collision.source_files(),
        )
        for collision in collisions
    ]


def _facet_root_records(
    raw: RawDocument, exc: FacetRootCollisionError
) -> list[CollisionRecord]:
    return [
        CollisionRecord(
            source=raw.source,
            reason=COLLISION_FACET_ROOT_DUPLICATED,
            identifier=raw.source_document_id,
            key=root,
            files=files,
        )
        for root, files in exc.roots.items()
    ]


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

    def exclude(self, raw: RawDocument, exc: Exception, reason: str) -> None:
        logger.warning(
            "Document %s rejeté (%s) : %s", raw.source_document_id, reason, exc
        )
        self.telemetry.emit(
            build_event(
                event_type=DOCUMENT_INVALIDATED,
                run_id=self.context.run_id,
                source=raw.source,
                payload={
                    "reason": reason,
                    "uid": raw.source_document_id,
                    "error": str(exc),
                },
                success=False,
                error_message=str(exc),
            )
        )
        self.telemetry.record_invalidation(
            InvalidatedDocument(
                source=raw.source,
                identifier=raw.source_document_id,
                reason=reason,
                error=str(exc),
                files=tuple(raw.payload["files"]),
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

    def declare_collisions(self, records: Sequence[CollisionRecord]) -> None:
        """Une par (document, clé)."""
        for record in records:
            self.telemetry.record_collision(record)
