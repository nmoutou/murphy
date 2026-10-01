"""Le vocabulaire des événements de télémétrie : leurs noms, et ceux qui portent un
compte. Tout événement émis est compté au bilan du run (``RunStatsAggregator``).
"""

# ---------------------------------------------------------------------------
# Constantes publiques (re-exportées depuis ici — audit.py les re-importe)
# ---------------------------------------------------------------------------

DOCUMENT_FETCHED = "document.fetched"
DOCUMENT_PARSED = "document.parsed"
# Écartés par le connecteur, un compteur par raison — HORS équation : un fichier écarté
# n'est pas un document vu. La raison est dans le NOM, le bilan la lit sans ventilation.
DOCUMENT_VERSION_SKIPPED = (
    "document.version_skipped"  # artefact d'export (versions.xml)
)
DOCUMENT_UNREADABLE = "document.unreadable"  # XML illisible (tronqué, encodage cassé)
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
# Un lien que la source a écrit mais qu'on ne sait pas écrire (``sens`` inconnu, ``@id``
# illisible, ``typelien`` qui ne peut pas être un verbe) : l'arête n'existe pas. Le
# COMPTER est ce qui l'empêche de disparaître en silence (ADR-048).
RELATION_UNKNOWN = "relation.unknown"

# Les collisions du run n'ont pas pu être écrites dans `MURPHY_META.collisions` : le
# bilan en compte que la collection ne montre pas. Un événement par écriture ratée ; il
# passe le run en `degraded` (ADR-049).
COLLISION_UNRECORDED = "collision.unrecorded"

SAGA_COMPENSATION_STARTED = "saga.compensation.triggered"
SAGA_COMPENSATION_COMPLETED = "saga.compensation.completed"
# Une compensation qui échoue laisse un écrit partiel (ex. Mongo inséré, son rollback
# raté) que RIEN d'autre ne compte : le document, lui, est déjà compté FAILED. Sans ce
# compteur, l'état corrompu resterait invisible au bilan — une perte sans compteur.
SAGA_COMPENSATION_FAILED = "saga.compensation.failed"


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
        DOCUMENT_VERSION_SKIPPED,  # émis une fois en fin de fetch → nombre d'artefacts
        DOCUMENT_UNREADABLE,  # émis une fois en fin de fetch → nombre d'illisibles
        RELATION_UNKNOWN,  # émis une fois par document → nombre de liens perdus
    }
)
"""Les événements dont ``payload[PAYLOAD_COUNT_KEY]`` EST leur poids d'agrégat. Tout autre
événement pèse 1, quoi que contienne son payload. Ajouter un émetteur porteur de
cardinalité, c'est l'ajouter ICI — sinon son lot ne compte que pour un."""


# ---------------------------------------------------------------------------
# Le vocabulaire complet — verrouillé par ``tests/golden/test_event_catalog.py``
# ---------------------------------------------------------------------------

EVENT_TYPES: frozenset[str] = frozenset(
    {
        # --- Cycle de vie d'un document ---
        DOCUMENT_FETCHED,
        DOCUMENT_PARSED,
        DOCUMENT_INVALIDATED,
        # Ce que le connecteur ÉCARTE, porteur de son `count`. Compté au bilan, mais
        # HORS équation : un fichier écarté n'est PAS un document vu, et `_status_from`
        # ne lit que `document.fetched` pour dénominateur — jamais ces compteurs.
        DOCUMENT_VERSION_SKIPPED,
        DOCUMENT_UNREADABLE,
        # --- Traitement ---
        DOCUMENT_PERSISTED,
        # La FUITE : un document vu, parsé, jamais ingéré. Le COMPTER est tout l'enjeu :
        # l'échec partait auparavant en `telemetry.log()`, donc en console SEULEMENT ;
        # tracé sans être compté, le run se déclarait « ok » en ayant perdu 98
        # documents. Un échec qui ne compte pas n'existe pas pour le bilan.
        DOCUMENT_FAILED,
        CHUNK_TRUNCATED,
        # --- Relations ---
        RELATION_UPSERTED,
        RELATION_PENDING,
        RELATION_PROMOTED,
        RELATION_UNKNOWN,
        # --- Collisions de métadonnées ---
        COLLISION_UNRECORDED,
        # --- Saga (erreurs de transaction) ---
        SAGA_COMPENSATION_STARTED,
        SAGA_COMPENSATION_COMPLETED,
        SAGA_COMPENSATION_FAILED,
    }
)
"""Les types d'événements que le pipeline émet. Un ensemble nommé et figé par golden :
un événement ajouté ou perdu se voit en revue, pas dans un bilan qui dérive."""
