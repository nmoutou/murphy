"""Nœud Kedro : parse les documents et sépare ceux à ingérer de ceux rejetés.

Un document qui parse part à l'ingestion, qu'il soit déjà en base ou non : la saga
réécrit en place (``replace_one`` Mongo, delete-puis-insert Qdrant, ``MERGE`` Neo4j). Un
document qui NE parse pas est rejeté (``document.invalidated``, dans l'audit) : il est
compté, pas silencieusement ignoré. Il n'y a pas de troisième voie « SKIP ».

Les collisions de métadonnées (ADR-049), celles d'un document parsé comme d'un document
refusé, sont comptées au bilan (``unknowns.collisions``) : un compte par (document, clé).
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
    CATEGORY_COLLISION,
    CATEGORY_LINK,
    CATEGORY_ROOT,
    CATEGORY_TAG,
)
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED, DOCUMENT_PARSED

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Rejection:
    """Comment un document écarté au parse est tracé : raison et log."""

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
    # WorkerTelemetry, pas TelemetryPort : ce nœud DÉCLARE (`record_unknown`), il
    # n'émet pas seulement. Le stack du hook (WorkerTelemetryStack) le fournit.
    telemetry: WorkerTelemetry,
    skip_unconfigured: bool,
) -> tuple[list[ParsedDocument], list[str]]:
    """Parse les documents : ceux qui parsent partent à l'ingestion, les autres sont rejetés.

    Un rejet (``ValidationError`` ou ``ParseError``) émet ``document.invalidated`` avec
    sa raison, son chemin source et le message d'erreur.

    C'est aussi le SITE DE PARSE — donc le site du signal et du curseur : le
    parser est pur et rend ses constats dans ``ParseResult`` ; ce nœud,
    qui tient la télémétrie, déclare les métadonnées, liens et racines non-configurés
    (``tags``, ``links``, ``roots``, TOUJOURS), puis applique le curseur
    ``skip_unconfigured`` — ``True`` retire les métadonnées non-configurées du document
    juste avant qu'il parte vers l'ingestion (ses liens non-configurés, eux, sont retirés
    à l'extraction). Compter d'abord, filtrer ensuite : le signal précède le filtre.
    Le curseur arrive déjà validé et arbitré par le plan du run (``run_plan.plan_run``).
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
    """Le résultat du parse, ou ``None`` pour un document rejeté — déjà tracé."""
    try:
        return parser.parse(raw)
    except CollisionError as exc:
        # Refusé, mais ses collisions sont le propos même du refus : elles comptent.
        site.declare_collisions(exc.collisions)
        site.exclude(raw, exc, _COLLISION_REJECTION)
    except ValidationError as exc:
        site.exclude(raw, exc, _VALIDATION_REJECTION)
    except ParseError as exc:
        # Document illisible. Toute autre exception sort du contrat de BaseParser :
        # c'est un bug du run (un document qu'aucun parser ne sait router), pas un
        # document à exclure — elle remonte et arrête le run.
        site.exclude(raw, exc, _PARSE_REJECTION)
    return None


def _apply_cursor(result: ParseResult, skip_unconfigured: bool) -> ParsedDocument:
    """Le CURSEUR — `skip` retire les métadonnées non-configurées du document, juste
    avant l'ingestion. `ParsedDocument` est frozen : on reconstruit."""
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
    """Le site de parse : ce qui trace un rejet, un signal ou un document parsé.

    La source n'est PAS lue du contexte : en run multi-source, `context.source` vaut
    None et effacerait l'attribution de source sur CHAQUE événement. Chaque `raw` porte
    sa vraie origine (`raw.source`), même quand le parsing échoue — c'est elle qui doit
    être tracée.
    """

    context: PipelineContext
    telemetry: WorkerTelemetry

    def exclude(self, raw: RawDocument, exc: Exception, rejection: _Rejection) -> None:
        """Un document écarté est COMPTÉ (``document.invalidated``), jamais ignoré."""
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
        """Le SIGNAL — toujours, et AVANT le curseur : la vigie de dérive DILA compte
        chaque métadonnée, lien et racine non-configurés au bilan de run, que la donnée
        soit ensuite ingérée ou retirée. `skip` n'efface jamais le signal."""
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
        """Document valide — compté parsé, en route vers l'ingestion."""
        self.telemetry.emit(
            build_event(
                event_type=DOCUMENT_PARSED,
                run_id=self.context.run_id,
                source=raw.source,
                document_id=parsed.identifier.serialize(),
            )
        )

    def declare_collisions(self, collisions: Sequence[Collision]) -> None:
        """Une collision par (document, clé) : un compte au bilan."""
        for collision in collisions:
            example = UnknownExample(
                identifier=collision.identifier,
                source_file=collision.values[0].source_file,
            )
            self.telemetry.record_unknown(CATEGORY_COLLISION, collision.key, example)
