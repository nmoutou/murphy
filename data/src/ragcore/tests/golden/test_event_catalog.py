"""Cliquet : ``EVENT_TYPES``, le contrat entre les sites d'émission et le bilan. Ajouter
un événement, c'est ajouter sa ligne ici, sciemment.
"""

from ragcore.core.telemetry_events import (
    COUNT_CARRYING_EVENTS,
    EVENT_TYPES,
    collision_count_key,
    invalidation_count_key,
)

GOLDEN = {
    "document.fetched",
    "document.parsed",
    "document.invalidated",
    "document.version_skipped",
    "document.unreadable",
    # Un fichier dont l'<ID> n'est pas le nom : la clé du flux (ADR-034 §1)
    "document.id_mismatch",
    # Une copie écartée par l'arbitrage, au profit d'une plus récente (ADR-036 §4)
    "document.superseded",
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
    "document.id_mismatch",  # nombre de fichiers dont l'<ID> n'est pas le nom
    "document.superseded",  # nombre de copies écartées par l'arbitrage
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


def test_the_reason_counters_keep_their_keys() -> None:
    """Les bilans de ``MURPHY_META`` se comparent d'un run à l'autre par ces clés."""
    assert collision_count_key("metadata") == "collision.metadata"
    assert invalidation_count_key("parse_error") == "document.invalidated.parse_error"
