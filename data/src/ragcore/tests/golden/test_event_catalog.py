"""Cliquet : ``EVENT_TYPES``, le contrat entre les sites d'émission et le bilan. Ajouter
un événement, c'est ajouter sa ligne ici, sciemment.
"""

from ragcore.core.telemetry_events import COUNT_CARRYING_EVENTS, EVENT_TYPES

GOLDEN = {
    "document.fetched",
    "document.parsed",
    "document.invalidated",
    "document.version_skipped",
    "document.unreadable",
    "document.persisted",
    # Vu, jamais ingéré : sans ce compteur, le run se déclarerait « ok »
    "document.failed",
    # Non nul = `CHUNKING_MAX_CHARS` incompatible avec la fenêtre du modèle
    "chunk.truncated",
    "relation.upserted",
    "relation.pending",
    "relation.promoted",
    # Un lien de la source qu'on ne sait pas écrire (ADR-024)
    "relation.unknown",
    "saga.compensation.triggered",
    "saga.compensation.completed",
    "saga.compensation.failed",
}


def test_the_vocabulary_is_exactly_the_golden_set() -> None:
    assert set(EVENT_TYPES) == GOLDEN, (
        "Le vocabulaire a changé. Si c'est voulu, mettre GOLDEN à jour ; "
        "sinon, un événement a été ajouté ou perdu sans décision."
    )


# Les événements porteurs de cardinalité : un émetteur qui renomme son payload casse ce
# cliquet au lieu de fausser le bilan.
GOLDEN_COUNT_CARRYING = {
    "document.fetched",  # nombre de documents vus
    "relation.upserted",  # nombre d'arêtes écrites
    "chunk.truncated",  # nombre de chunks raccourcis
    "document.version_skipped",  # nombre d'artefacts d'export écartés
    "document.unreadable",  # nombre de fichiers illisibles écartés
    "relation.unknown",  # nombre de liens perdus d'un document
}


def test_count_carrying_events_are_exactly_the_golden_set() -> None:
    assert set(COUNT_CARRYING_EVENTS) == GOLDEN_COUNT_CARRYING, (
        "L'ensemble des events porteurs de cardinalité a changé. Si c'est voulu, mettre "
        "GOLDEN_COUNT_CARRYING à jour ; sinon, le poids d'un lot vient de basculer sans "
        "décision — un run de 1121 documents pourrait se compter pour 1."
    )


def test_every_count_carrying_event_is_in_the_vocabulary() -> None:
    assert COUNT_CARRYING_EVENTS <= EVENT_TYPES
