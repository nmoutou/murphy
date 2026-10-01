"""Catalogue complet des event types et de leurs comportements de télémétrie.

Source de vérité unique : les constantes et leur routage vers les backends
sont déclarés au même endroit.

Comportement par défaut pour tout event_type non listé :
  level="info", log=True, track_mongo=True, aggregate=True
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
DOCUMENT_SKIPPED = "document.skipped"  # écarté par le connecteur — HORS équation
DOCUMENT_INVALIDATED = "document.invalidated"
DOCUMENT_PERSISTED = "document.persisted"
DOCUMENT_FAILED = "document.failed"  # vu, jamais ingéré — la FUITE

# Un chunk trop long pour la fenêtre du modèle, raccourci pour sauver son document. Ce
# n'est PAS une fuite (le document est ingéré) mais ce n'est pas rien : la fin du chunk
# n'est pas indexée. Non nul = le `CHUNKING_MAX_CHARS` configuré est incompatible avec le modèle.
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
# Une compensation qui échoue laisse un écrit partiel (ex. Mongo inséré, son rollback
# raté) que RIEN d'autre ne compte : le document, lui, est déjà compté FAILED. Sans ce
# compteur, l'état corrompu resterait invisible au bilan — une perte sans compteur.
SAGA_COMPENSATION_FAILED = "saga.compensation.failed"

MAINTENANCE_NUKE_ALL_EXECUTED = "maintenance.nuke_all.executed"


# ---------------------------------------------------------------------------
# Contrat de comptage : événement UNITAIRE vs PORTEUR DE CARDINALITÉ
# ---------------------------------------------------------------------------
# La plupart des événements sont UNITAIRES : ils tintent une fois pour une chose
# (un document persisté = 1). Quelques-uns sont émis UNE FOIS POUR UN LOT et portent
# leur cardinalité dans ``payload[PAYLOAD_COUNT_KEY]`` : ``document.fetched`` avec le
# nombre de documents vus, ``relation.upserted`` avec le nombre d'arêtes écrites.
# L'agrégateur (``_weight_of``) lit ce ``count`` — mais SEULEMENT pour les événements
# listés ici. Ailleurs, un ``count`` dans le payload est du bruit, pas un poids.
#
# **Pourquoi cet ensemble EXISTE et n'est pas implicite.** Avant, ``_weight_of`` lisait
# ``payload["count"]`` pour n'importe quel événement, au seul motif que la clé s'appelait
# ``count``. Le contrat était invisible : renommer le payload d'un émetteur (``count`` →
# ``n``) aurait fait retomber son poids à 1 SANS un seul test rouge — le bilan aurait menti
# en silence sur un run de 1121 documents. Nommer l'ensemble et la clé grave le contrat :
# le test ``golden/test_event_catalog`` le verrouille, et un émetteur qui prétend porter
# une cardinalité sans figurer ici est un bug visible, pas une dérive muette.
PAYLOAD_COUNT_KEY = "count"
"""La clé, sous laquelle un événement porteur de cardinalité pose son compte. UNE seule
clé pour tous : un émetteur qui écrit ``payload={"count": n}`` et un lecteur qui lit
``payload[PAYLOAD_COUNT_KEY]`` ne peuvent pas diverger par accident."""

COUNT_CARRYING_EVENTS: frozenset[str] = frozenset(
    {
        DOCUMENT_FETCHED,  # émis une fois par lot fetché → nombre de documents vus
        RELATION_UPSERTED,  # émis une fois par batch → nombre d'arêtes écrites
        CHUNK_TRUNCATED,  # émis une fois en fin de run → nombre de chunks raccourcis
        DOCUMENT_SKIPPED,  # émis une fois par raison → nombre de fichiers écartés
    }
)
"""Les événements dont ``payload[PAYLOAD_COUNT_KEY]`` EST leur poids d'agrégat. Tout autre
événement pèse 1, quoi que contienne son payload. Ajouter un émetteur porteur de
cardinalité, c'est l'ajouter ICI — sinon son lot ne compte que pour un."""


# ---------------------------------------------------------------------------
# Catalogue : event_type → EventBehavior
# ---------------------------------------------------------------------------
# Champs :
#   level       : niveau de log textuel ("info" | "warning" | "error")
#   log         : stdout via ConsoleLogTelemetry
#   track_mongo : collection audit MongoDB
#   aggregate   : RunStatsAggregator (RunSummary)
# ---------------------------------------------------------------------------

EVENT_CATALOG: dict[str, EventBehavior] = {
    # --- Cycle de vie du pipeline ---
    # Hors agrégat : le bilan les porte déjà en `started_at`, `ended_at` et `status`.
    PIPELINE_RUN_STARTED: EventBehavior(
        level="info",
        log=True,
        track_mongo=True,
        aggregate=False,
    ),
    PIPELINE_RUN_COMPLETED: EventBehavior(
        level="info",
        log=True,
        track_mongo=True,
        aggregate=False,
    ),
    PIPELINE_RUN_FAILED: EventBehavior(
        level="error",
        log=True,
        track_mongo=True,
        aggregate=False,
    ),
    # --- Cycle de vie d'un document ---
    DOCUMENT_FETCHED: EventBehavior(
        level="info",
        log=False,
        track_mongo=False,
        aggregate=True,
    ),
    DOCUMENT_PARSED: EventBehavior(
        level="info",
        log=False,
        track_mongo=False,
        aggregate=True,
    ),
    DOCUMENT_INVALIDATED: EventBehavior(
        level="warning",
        log=True,
        track_mongo=True,
        aggregate=True,
    ),
    DOCUMENT_SKIPPED: EventBehavior(
        # Ce que le connecteur ÉCARTE (artefact d'export, fichier illisible), un événement
        # par raison, porteur de son `count`. Compté au bilan, mais HORS équation : un
        # fichier écarté n'est PAS un document vu, et `_status_from` ne lit que
        # `document.fetched` pour dénominateur — jamais ce compteur.
        level="warning",
        log=False,
        track_mongo=True,
        aggregate=True,
    ),
    # --- Traitement ---
    DOCUMENT_PERSISTED: EventBehavior(
        level="info",
        log=True,
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
        track_mongo=True,
        aggregate=True,
    ),
    CHUNK_TRUNCATED: EventBehavior(
        level="warning",
        log=True,
        track_mongo=True,
        aggregate=True,
    ),
    # --- Relations ---
    RELATION_UPSERTED: EventBehavior(
        level="warning",
        log=False,
        track_mongo=False,
        aggregate=True,
    ),
    RELATION_PENDING: EventBehavior(
        # Une arête différée est une DONNÉE, pas un vide : elle va en base méta,
        # au même titre que le cache §13 qu'elle accompagne.
        level="warning",
        log=False,
        track_mongo=True,
        aggregate=True,
    ),
    RELATION_PROMOTED: EventBehavior(
        level="info",
        log=False,
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
        track_mongo=False,
        aggregate=True,
    ),
    # --- Saga (erreurs de transaction) ---
    SAGA_COMPENSATION_STARTED: EventBehavior(
        level="error",
        log=True,
        track_mongo=True,
        aggregate=True,
    ),
    SAGA_COMPENSATION_COMPLETED: EventBehavior(
        level="warning",
        log=True,
        track_mongo=True,
        aggregate=True,
    ),
    SAGA_COMPENSATION_FAILED: EventBehavior(
        level="error",
        log=True,
        track_mongo=True,
        aggregate=True,
    ),
    # --- Maintenance ---
    MAINTENANCE_NUKE_ALL_EXECUTED: EventBehavior(
        level="warning",
        log=True,
        track_mongo=True,
        aggregate=False,
    ),
}
