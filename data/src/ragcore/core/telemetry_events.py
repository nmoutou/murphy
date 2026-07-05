"""Catalogue complet des event types et de leurs comportements de télémétrie.

Source de vérité unique : les constantes et leur routage vers les backends
sont déclarés au même endroit.

Comportement par défaut pour tout event_type non listé :
  level="info", log=True, track_jsonl=True, track_mongo=True, aggregate=True
"""

from ragcore.core.services.telemetry_registry import EventBehavior

# ---------------------------------------------------------------------------
# Constantes publiques (re-exportées depuis ici — audit.py les re-importe)
# ---------------------------------------------------------------------------

PIPELINE_RUN_STARTED              = "pipeline.run.started"
PIPELINE_RUN_COMPLETED            = "pipeline.run.completed"
PIPELINE_RUN_FAILED               = "pipeline.run.failed"

DOCUMENT_FETCHED                  = "document.fetched"
DOCUMENT_PARSED                   = "document.parsed"
DOCUMENT_SKIPPED                  = "document.skipped"   # conservé pour rétrocompat JSONL
DOCUMENT_INVALIDATED              = "document.invalidated"
DOCUMENT_CHUNKED                  = "document.chunked"
DOCUMENT_EMBEDDED                 = "document.embedded"
DOCUMENT_PERSISTED                = "document.persisted"
DOCUMENT_REPLACED                 = "document.replaced"
DOCUMENT_DELETED                  = "document.deleted"

RELATION_UPSERTED                 = "relation.upserted"

SAGA_COMPENSATION_STARTED         = "saga.compensation.triggered"
SAGA_COMPENSATION_COMPLETED       = "saga.compensation.completed"

MAINTENANCE_CLEANUP_EXECUTED      = "maintenance.cleanup.executed"
MAINTENANCE_FORCE_DROP_EXECUTED   = "maintenance.force_drop.executed"


# ---------------------------------------------------------------------------
# Catalogue : event_type → EventBehavior
# ---------------------------------------------------------------------------
# Champs :
#   level       : niveau de log textuel ("info" | "warning" | "error")
#   log         : stdout via ConsoleLogTelemetry
#   track_jsonl : fichier JSONL local (audit complet)
#   track_mongo : collection audit MongoDB
#   aggregate   : RunStatsAggregator (RunSummary + stats JSON)
# ---------------------------------------------------------------------------

EVENT_CATALOG: dict[str, EventBehavior] = {

    # --- Cycle de vie du pipeline ---
    PIPELINE_RUN_STARTED: EventBehavior(
        level="info", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),
    PIPELINE_RUN_COMPLETED: EventBehavior(
        level="info", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),
    PIPELINE_RUN_FAILED: EventBehavior(
        level="error", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),

    # --- Cycle de vie d'un document ---
    DOCUMENT_FETCHED: EventBehavior(
        level="info", log=False, track_jsonl=True, track_mongo=False, aggregate=True,
    ),
    DOCUMENT_PARSED: EventBehavior(
        level="info", log=False, track_jsonl=True, track_mongo=False, aggregate=True,
    ),
    DOCUMENT_INVALIDATED: EventBehavior(
        level="warning", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),
    DOCUMENT_SKIPPED: EventBehavior(
        # Plus émis après refonte, conservé pour compatibilité fichiers JSONL existants
        level="warning", log=False, track_jsonl=True, track_mongo=False, aggregate=False,
    ),

    # --- Traitement ---
    DOCUMENT_PERSISTED: EventBehavior(
        level="info", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),
    DOCUMENT_REPLACED: EventBehavior(
        level="info", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),
    DOCUMENT_DELETED: EventBehavior(
        level="info", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),

    # --- Relations ---
    RELATION_UPSERTED: EventBehavior(
        level="warning", log=False, track_jsonl=True, track_mongo=False, aggregate=True,
    ),

    # --- Saga (erreurs de transaction) ---
    SAGA_COMPENSATION_STARTED: EventBehavior(
        level="error", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),
    SAGA_COMPENSATION_COMPLETED: EventBehavior(
        level="warning", log=True, track_jsonl=True, track_mongo=True, aggregate=True,
    ),

    # --- Maintenance ---
    MAINTENANCE_CLEANUP_EXECUTED: EventBehavior(
        level="info", log=True, track_jsonl=True, track_mongo=False, aggregate=False,
    ),
    MAINTENANCE_FORCE_DROP_EXECUTED: EventBehavior(
        level="warning", log=True, track_jsonl=True, track_mongo=True, aggregate=False,
    ),
}
