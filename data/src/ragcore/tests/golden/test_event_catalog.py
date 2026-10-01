"""CLIQUET — le vocabulaire des événements.

Ce n'est pas un test : c'est un verrou. EVENT_TYPES est le contrat entre les sites
d'émission et le bilan du run. En figer le contenu ici oblige toute modification à
passer par ce fichier, donc à se voir en revue.

Ajouter un événement = ajouter sa ligne ci-dessous, sciemment.
"""

from ragcore.core.telemetry_events import COUNT_CARRYING_EVENTS, EVENT_TYPES

GOLDEN = {
    "document.fetched",
    "document.parsed",
    "document.invalidated",
    "document.version_skipped",
    "document.unreadable",
    "document.persisted",
    # La FUITE : vu, jamais ingéré. Sans ce compteur, le run se déclare « ok » en
    # perdant des documents.
    "document.failed",
    # Pas une fuite (le document est ingéré) mais pas rien : la fin du chunk n'est pas
    # indexée. Non nul = `CHUNKING_MAX_CHARS` incompatible avec la fenêtre du modèle.
    "chunk.truncated",
    "relation.upserted",
    "relation.pending",
    "relation.promoted",
    "saga.compensation.triggered",
    "saga.compensation.completed",
    "saga.compensation.failed",
}


def test_the_vocabulary_is_exactly_the_golden_set() -> None:
    assert set(EVENT_TYPES) == GOLDEN, (
        "Le vocabulaire a changé. Si c'est voulu, mettre GOLDEN à jour ; "
        "sinon, un événement a été ajouté ou perdu sans décision."
    )


# Les events PORTEURS DE CARDINALITÉ — émis une fois pour un lot, leur poids d'agrégat
# est ``payload["count"]``. Le figer ici verrouille le contrat de F15 : un émetteur qui
# renomme son payload, ou qui prétend porter un compte sans figurer ici, casse ce cliquet
# au lieu de fausser le bilan en silence.
GOLDEN_COUNT_CARRYING = {
    "document.fetched",  # nombre de documents vus
    "relation.upserted",  # nombre d'arêtes écrites
    "chunk.truncated",  # nombre de chunks raccourcis
    "document.version_skipped",  # nombre d'artefacts d'export écartés
    "document.unreadable",  # nombre de fichiers illisibles écartés
}


def test_count_carrying_events_are_exactly_the_golden_set() -> None:
    assert set(COUNT_CARRYING_EVENTS) == GOLDEN_COUNT_CARRYING, (
        "L'ensemble des events porteurs de cardinalité a changé. Si c'est voulu, mettre "
        "GOLDEN_COUNT_CARRYING à jour ; sinon, le poids d'un lot vient de basculer sans "
        "décision — un run de 1121 documents pourrait se compter pour 1."
    )


def test_every_count_carrying_event_is_in_the_vocabulary() -> None:
    assert COUNT_CARRYING_EVENTS <= EVENT_TYPES
