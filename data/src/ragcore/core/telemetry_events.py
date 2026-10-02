"""Le vocabulaire des événements de télémétrie : leurs noms, et ceux qui portent un
compte. Tout événement émis est compté au bilan du run (``RunStatsAggregator``).
"""

DOCUMENT_FETCHED = "document.fetched"
DOCUMENT_PARSED = "document.parsed"
# Écartés par le connecteur, un compteur par raison, hors équation de complétude : un
# fichier écarté n'est pas un document vu.
DOCUMENT_VERSION_SKIPPED = (
    "document.version_skipped"  # artefact d'export (versions.xml)
)
DOCUMENT_UNREADABLE = "document.unreadable"  # XML illisible (tronqué, encodage cassé)
DOCUMENT_INVALIDATED = "document.invalidated"
DOCUMENT_PERSISTED = "document.persisted"
DOCUMENT_FAILED = "document.failed"  # vu, jamais ingéré : une fuite

# Chunk raccourci à la fenêtre du modèle : le document est ingéré, mais la fin du chunk
# n'est pas indexée. Non nul = `CHUNKING_MAX_CHARS` incompatible avec le modèle.
CHUNK_TRUNCATED = "chunk.truncated"

RELATION_UPSERTED = "relation.upserted"
RELATION_PENDING = "relation.pending"  # cible absente → pendante
RELATION_PROMOTED = "relation.promoted"  # pendante enfin résolue
# Un lien de la source qu'on ne sait pas écrire (``sens`` inconnu, ``@id`` illisible,
# ``typelien`` impossible en verbe) : compté pour ne pas disparaître en silence (ADR-024).
RELATION_UNKNOWN = "relation.unknown"

SAGA_COMPENSATION_STARTED = "saga.compensation.triggered"
SAGA_COMPENSATION_COMPLETED = "saga.compensation.completed"
# Une compensation ratée laisse un écrit partiel que rien d'autre ne compte : le
# document, lui, est déjà compté FAILED.
SAGA_COMPENSATION_FAILED = "saga.compensation.failed"


# ---------------------------------------------------------------------------
# Contrat de comptage : événement unitaire ou porteur de cardinalité
# ---------------------------------------------------------------------------
# La plupart des événements comptent pour un. Quelques-uns sont émis une fois par lot
# et portent leur cardinalité dans ``payload[PAYLOAD_COUNT_KEY]`` ; l'agrégateur ne la
# lit que pour les événements listés ici.
PAYLOAD_COUNT_KEY = "count"

COUNT_CARRYING_EVENTS: frozenset[str] = frozenset(
    {
        DOCUMENT_FETCHED,  # émis une fois par lot fetché → nombre de documents vus
        RELATION_UPSERTED,  # émis une fois par batch → nombre d'arêtes écrites
        CHUNK_TRUNCATED,  # émis une fois en fin de run → nombre de chunks raccourcis
        DOCUMENT_VERSION_SKIPPED,  # émis une fois en fin de fetch → nombre d'artefacts
        DOCUMENT_UNREADABLE,  # émis une fois en fin de fetch → nombre d'illisibles
        RELATION_UNKNOWN,  # émis une fois par document → nombre de liens perdus
    }
)
"""Tout autre événement pèse 1, quoi que contienne son payload : un nouvel émetteur
porteur de cardinalité doit être ajouté ici."""


# ---------------------------------------------------------------------------
# Le vocabulaire complet — verrouillé par ``tests/golden/test_event_catalog.py``
# ---------------------------------------------------------------------------

EVENT_TYPES: frozenset[str] = frozenset(
    {
        # --- Cycle de vie d'un document ---
        DOCUMENT_FETCHED,
        DOCUMENT_PARSED,
        DOCUMENT_INVALIDATED,
        # Écartés par le connecteur : hors équation de complétude
        DOCUMENT_VERSION_SKIPPED,
        DOCUMENT_UNREADABLE,
        # --- Traitement ---
        DOCUMENT_PERSISTED,
        DOCUMENT_FAILED,
        CHUNK_TRUNCATED,
        # --- Relations ---
        RELATION_UPSERTED,
        RELATION_PENDING,
        RELATION_PROMOTED,
        RELATION_UNKNOWN,
        # --- Saga (erreurs de transaction) ---
        SAGA_COMPENSATION_STARTED,
        SAGA_COMPENSATION_COMPLETED,
        SAGA_COMPENSATION_FAILED,
    }
)
"""Figé par golden : un événement ajouté ou perdu se voit en revue."""
