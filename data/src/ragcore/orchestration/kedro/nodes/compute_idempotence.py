"""Nœud Kedro : parse les documents et décide de l'opération (INSERT vs UPDATE).

Deux issues seulement pour un document qui parse : INSERT ou UPDATE — l'idempotence se lit
sur la présence de l'identifiant dans le manifest, jamais sur un hash de contenu. Un
document qui NE parse pas est rejeté (entrée EXCLUDED au manifest) : il est compté, pas
silencieusement ignoré. Il n'y a pas de troisième voie « SKIP ».
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from ragcore.application.run_context import PipelineContext
from ragcore.core.exceptions import ParseError, ValidationError
from ragcore.core.models.audit import build_event
from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import Operation
from ragcore.core.models.manifest import ManifestEntry
from ragcore.core.ports.manifest_repository import ManifestRepository
from ragcore.core.ports.parser import BaseParser, ParseResult
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.services.exclusion_reasons import (
    REASON_PARSE_ERROR,
    REASON_VALIDATION_ERROR,
)
from ragcore.core.services.idempotence import determine_operation
from ragcore.core.services.unknown_categories import (
    CATEGORY_ROOT,
    CATEGORY_UNCONFIGURED_TAG,
)
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED, DOCUMENT_PARSED

logger = logging.getLogger(__name__)

_UNCONFIGURED_BEHAVIORS = frozenset({"ingest", "skip"})


def _resolve_unconfigured_behavior(exportation_params: dict[str, object]) -> str:
    """Le curseur ``exportation.unconfigured`` — validé au démarrage, jamais deviné.

    Une valeur inconnue (coquille ``skipp``) doit échouer EN NOMMANT les valeurs
    valides, pas retomber en silence sur le défaut : un run qui n'applique pas le
    comportement qu'on croit avoir demandé est un échec silencieux (même règle que
    ``resolve_sources`` dans ``run_parameters``).
    """
    value = str(exportation_params.get("unconfigured", "ingest")).strip().lower()
    if value not in _UNCONFIGURED_BEHAVIORS:
        valides = ", ".join(sorted(_UNCONFIGURED_BEHAVIORS))
        msg = f"exportation.unconfigured invalide : {value!r}. Valeurs : {valides}."
        raise ValueError(msg)
    return value


@dataclass(frozen=True)
class _Rejection:
    """Comment un document écarté au parse est tracé : raison, log, manifeste."""

    reason: str
    log_message: str
    prefixes_manifest_reason: bool
    """La raison du manifeste préfixe-t-elle le message d'erreur de ``reason`` ?"""


_VALIDATION_REJECTION = _Rejection(
    REASON_VALIDATION_ERROR, "Document invalidé %s — rejeté", False
)
_PARSE_REJECTION = _Rejection(
    REASON_PARSE_ERROR, "Erreur parsing document %s — rejeté", True
)


def compute_idempotence_node(
    raw_documents: list[RawDocument],
    parser: BaseParser,
    manifest_repo: ManifestRepository,
    pipeline_context: PipelineContext,
    # WorkerTelemetry, pas TelemetryPort : ce nœud DÉCLARE (`record_unknown`), il
    # n'émet pas seulement. Le stack du hook (RegistryAwareTelemetry) le fournit.
    telemetry: WorkerTelemetry,
    pipeline_runtime: AsyncRuntime,
    exportation_params: dict[str, object],
) -> tuple[list[tuple[ParsedDocument, Operation]], list[str]]:
    """Parse documents and determine which need processing (INSERT vs UPDATE).

    Les documents rejetés (ValidationError) sont tracés dans le manifest avec
    l'opération EXCLUDED et un message de raison.

    C'est aussi le SITE DE PARSE — donc le site du signal et du curseur (cadrage
    B-00-d) : le parser est pur et rend ses constats dans ``ParseResult`` ; ce nœud,
    qui tient la télémétrie, déclare les balises non-configurées (``tag.unconfigured``,
    TOUJOURS), puis applique le curseur ``exportation.unconfigured`` — ``skip`` retire
    les métadonnées non-configurées du document juste avant qu'il parte vers
    l'ingestion. Compter d'abord, filtrer ensuite : le signal précède le filtre.
    """
    skip_unconfigured = _resolve_unconfigured_behavior(exportation_params) == "skip"
    site = _ParseSite(manifest_repo, pipeline_context, telemetry, pipeline_runtime)
    to_process: list[tuple[ParsedDocument, Operation]] = []
    to_skip: list[str] = []

    for raw in raw_documents:
        try:
            result = parser.parse(raw)
        except ValidationError as exc:
            site.exclude(raw, exc, _VALIDATION_REJECTION)
            to_skip.append(raw.source_document_id)
            continue
        except ParseError as exc:
            # Document illisible. Toute autre exception sort du contrat de BaseParser :
            # c'est un bug du run (un document qu'aucun parser ne sait router), pas un
            # document à exclure — elle remonte et arrête le run.
            site.exclude(raw, exc, _PARSE_REJECTION)
            to_skip.append(raw.source_document_id)
            continue

        site.declare_signals(result)
        parsed = _apply_cursor(result, skip_unconfigured)
        to_process.append((parsed, site.decide_operation(raw, parsed)))

    return to_process, to_skip


def _apply_cursor(result: ParseResult, skip_unconfigured: bool) -> ParsedDocument:
    """Le CURSEUR — `skip` retire les métadonnées non-configurées du document, juste
    avant l'ingestion. `ParsedDocument` est frozen : on reconstruit."""
    parsed = result.document
    if not skip_unconfigured or not result.unconfigured_keys:
        return parsed
    stripped = set(result.unconfigured_keys)
    return parsed.model_copy(
        update={
            "metadata": {
                key: value
                for key, value in parsed.metadata.items()
                if key not in stripped
            }
        }
    )


@dataclass(frozen=True)
class _ParseSite:
    """Le site de parse : ce qui trace un rejet, un signal ou une décision.

    La source n'est PAS lue du contexte : en run multi-source, `context.source` vaut
    None et effacerait l'attribution de source sur CHAQUE événement et entrée de
    manifeste. Chaque `raw` porte sa vraie origine (`raw.source`), même quand le parsing
    échoue — c'est elle qui doit être tracée.
    """

    manifest_repo: ManifestRepository
    context: PipelineContext
    telemetry: WorkerTelemetry
    runtime: AsyncRuntime

    def exclude(self, raw: RawDocument, exc: Exception, rejection: _Rejection) -> None:
        """Un document écarté est COMPTÉ et inscrit au manifeste (``EXCLUDED``)."""
        logger.warning(rejection.log_message, raw.source_document_id)
        self._emit_invalidated(raw, exc, rejection)
        reason = (
            f"{rejection.reason}: {exc}"
            if rejection.prefixes_manifest_reason
            else str(exc)
        )
        self._record_excluded(raw, reason)

    def _emit_invalidated(
        self, raw: RawDocument, exc: Exception, rejection: _Rejection
    ) -> None:
        self.telemetry.emit(
            build_event(
                event_type=DOCUMENT_INVALIDATED,
                run_id=self.context.run_id,
                owner_id=self.context.owner_id,
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

    def _record_excluded(self, raw: RawDocument, reason: str) -> None:
        self.runtime.run(
            self.manifest_repo.append(
                ManifestEntry(
                    identifier=None,
                    source_path=raw.source_document_id,
                    owner_id=self.context.owner_id,
                    source=raw.source,
                    operation=Operation.EXCLUDED,
                    reason=reason,
                    processed_at=datetime.now(UTC),
                )
            )
        )

    def declare_signals(self, result: ParseResult) -> None:
        """Le SIGNAL — toujours, et AVANT le curseur : la vigie de dérive DILA compte
        chaque balise/racine non-configurée au bilan de run, que la donnée soit ensuite
        ingérée ou retirée. `skip` n'efface jamais le signal."""
        for tag in result.unconfigured_tags:
            self.telemetry.record_unknown(CATEGORY_UNCONFIGURED_TAG, tag)
        for root in result.unknown_roots:
            self.telemetry.record_unknown(CATEGORY_ROOT, root)

    def decide_operation(self, raw: RawDocument, parsed: ParsedDocument) -> Operation:
        """Document valide — l'opération (INSERT ou UPDATE) se lit au manifeste."""
        manifest_entry = self.runtime.run(
            self.manifest_repo.last_for_identifier(parsed.identifier, parsed.owner_id)
        )
        operation = determine_operation(manifest_entry)
        self.telemetry.emit(
            build_event(
                event_type=DOCUMENT_PARSED,
                run_id=self.context.run_id,
                owner_id=self.context.owner_id,
                source=raw.source,
                document_id=parsed.identifier.serialize(),
                payload={"operation": operation.value},
            )
        )
        return operation
