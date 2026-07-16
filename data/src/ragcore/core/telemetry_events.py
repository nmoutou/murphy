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

PIPELINE_RUN_STARTED = "pipeline.run.started"
PIPELINE_RUN_COMPLETED = "pipeline.run.completed"
PIPELINE_RUN_FAILED = "pipeline.run.failed"

DOCUMENT_FETCHED = "document.fetched"
DOCUMENT_PARSED = "document.parsed"
DOCUMENT_SKIPPED = "document.skipped"  # conservé pour rétrocompat JSONL
DOCUMENT_INVALIDATED = "document.invalidated"
DOCUMENT_CHUNKED = "document.chunked"
DOCUMENT_EMBEDDED = "document.embedded"
DOCUMENT_PERSISTED = "document.persisted"
DOCUMENT_FAILED = "document.failed"  # vu, jamais ingéré — la FUITE
DOCUMENT_REPLACED = "document.replaced"
DOCUMENT_DELETED = "document.deleted"

# Un chunk trop long pour la fenêtre du modèle, raccourci pour sauver son document. Ce
# n'est PAS une fuite (le document est ingéré) mais ce n'est pas rien : la fin du chunk
# n'est pas indexée. Non nul = le `chunk_size` configuré est incompatible avec le modèle.
CHUNK_TRUNCATED = "chunk.truncated"

RELATION_UPSERTED = "relation.upserted"
RELATION_PENDING = "relation.pending"  # cible absente → cache §13
RELATION_PROMOTED = "relation.promoted"  # pendante enfin résolue

# La télémétrie qui n'a pas su s'écrire. L'audit observe le run ; ce compteur observe
# l'audit — sans lui, un backend défaillant rendrait TOUS les autres compteurs
# invérifiables sans que rien ne le dise.
AUDIT_WRITE_FAILED = "audit.write.failed"

SAGA_COMPENSATION_STARTED = "saga.compensation.triggered"
SAGA_COMPENSATION_COMPLETED = "saga.compensation.completed"

MAINTENANCE_CLEANUP_EXECUTED = "maintenance.cleanup.executed"
MAINTENANCE_NUKE_ALL_EXECUTED = "maintenance.nuke_all.executed"


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
        level="info",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    PIPELINE_RUN_COMPLETED: EventBehavior(
        level="info",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    PIPELINE_RUN_FAILED: EventBehavior(
        level="error",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    # --- Cycle de vie d'un document ---
    DOCUMENT_FETCHED: EventBehavior(
        level="info",
        log=False,
        track_jsonl=True,
        track_mongo=False,
        aggregate=True,
    ),
    DOCUMENT_PARSED: EventBehavior(
        level="info",
        log=False,
        track_jsonl=True,
        track_mongo=False,
        aggregate=True,
    ),
    DOCUMENT_INVALIDATED: EventBehavior(
        level="warning",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    DOCUMENT_SKIPPED: EventBehavior(
        # Plus émis après refonte, conservé pour compatibilité fichiers JSONL existants
        level="warning",
        log=False,
        track_jsonl=True,
        track_mongo=False,
        aggregate=False,
    ),
    # --- Traitement ---
    DOCUMENT_PERSISTED: EventBehavior(
        level="info",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    # La FUITE : un document vu, parsé, jamais ingéré. `aggregate=True` est tout l'enjeu —
    # l'échec partait auparavant en `telemetry.log()`, donc en console SEULEMENT : il était
    # tracé sans être compté, et le run se déclarait « ok » en ayant perdu 98 documents.
    # Un échec qui ne compte pas est un échec qui n'existe pas pour le bilan.
    DOCUMENT_FAILED: EventBehavior(
        level="error",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    CHUNK_TRUNCATED: EventBehavior(
        level="warning",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    DOCUMENT_REPLACED: EventBehavior(
        level="info",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    DOCUMENT_DELETED: EventBehavior(
        level="info",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    # --- Relations ---
    RELATION_UPSERTED: EventBehavior(
        level="warning",
        log=False,
        track_jsonl=True,
        track_mongo=False,
        aggregate=True,
    ),
    RELATION_PENDING: EventBehavior(
        # Une arête différée est une DONNÉE, pas un vide : elle va en base méta,
        # au même titre que le cache §13 qu'elle accompagne.
        level="warning",
        log=False,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    RELATION_PROMOTED: EventBehavior(
        level="info",
        log=False,
        track_jsonl=True,
        track_mongo=False,
        aggregate=True,
    ),
    # --- La télémétrie qui se surveille elle-même ---
    # `track_mongo=False`, et ce n'est pas un oubli : écrire en Mongo qu'on n'a pas su
    # écrire en Mongo est un serpent qui se mord la queue — au mieux ça échoue aussi, au
    # pire ça récurse. Le compteur vit dans l'AGRÉGAT (mémoire, ne peut pas échouer sur du
    # réseau) et voyage jusqu'au bilan par le monoïde `RunStats`, comme les autres.
    #
    # `aggregate=True` est tout l'enjeu, exactement comme pour `document.failed` : les
    # quatre points qui avalaient une écriture ratée la LOGGAIENT déjà (`_LOGGER.warning`).
    # Le problème n'a jamais été qu'on ne le disait pas — c'est qu'on ne le COMPTAIT pas,
    # donc que le bilan ne pouvait pas en tenir compte. Un échec qui ne compte pas est un
    # échec qui n'existe pas pour le statut du run.
    AUDIT_WRITE_FAILED: EventBehavior(
        level="error",
        log=True,
        track_jsonl=True,
        track_mongo=False,
        aggregate=True,
    ),
    # --- Saga (erreurs de transaction) ---
    SAGA_COMPENSATION_STARTED: EventBehavior(
        level="error",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    SAGA_COMPENSATION_COMPLETED: EventBehavior(
        level="warning",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=True,
    ),
    # --- Maintenance ---
    MAINTENANCE_CLEANUP_EXECUTED: EventBehavior(
        level="info",
        log=True,
        track_jsonl=True,
        track_mongo=False,
        aggregate=False,
    ),
    MAINTENANCE_NUKE_ALL_EXECUTED: EventBehavior(
        level="warning",
        log=True,
        track_jsonl=True,
        track_mongo=True,
        aggregate=False,
    ),
}
