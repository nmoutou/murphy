"""CLIQUET — le catalogue d'événements.

Ce n'est pas un test : c'est un verrou. EVENT_CATALOG est le contrat entre les
sites d'émission et les backends de télémétrie. En figer le contenu ici oblige
toute modification à passer par ce fichier, donc à se voir en revue.

Ajouter un événement = ajouter sa ligne ci-dessous, sciemment.
"""

from ragcore.core.services.telemetry_registry import EventBehavior
from ragcore.core.telemetry_events import COUNT_CARRYING_EVENTS, EVENT_CATALOG

# event_type -> aggregate
GOLDEN: dict[str, bool] = {
    # Hors agrégat : `started_at`, `ended_at` et `status` du bilan les disent déjà.
    "pipeline.run.started": False,
    "pipeline.run.completed": False,
    "pipeline.run.failed": False,
    "document.fetched": True,
    "document.parsed": True,
    "document.invalidated": True,
    "document.version_skipped": True,
    "document.unreadable": True,
    "document.persisted": True,
    # La FUITE : vu, jamais ingéré. `aggregate=True` est l'enjeu — sans lui l'échec
    # est tracé mais pas compté, et le run se déclare « ok » en perdant des documents.
    "document.failed": True,
    # Pas une fuite (le document est ingéré) mais pas rien : la fin du chunk n'est pas
    # indexée. Non nul = `CHUNKING_MAX_CHARS` incompatible avec la fenêtre du modèle.
    "chunk.truncated": True,
    "relation.upserted": True,
    "relation.pending": True,
    "relation.promoted": True,
    "saga.compensation.triggered": True,
    "saga.compensation.completed": True,
    "saga.compensation.failed": True,
}


def test_catalog_has_exactly_the_golden_events() -> None:
    assert set(EVENT_CATALOG) == set(GOLDEN), (
        "Le catalogue a changé. Si c'est voulu, mettre GOLDEN à jour ; "
        "sinon, un événement a été ajouté ou perdu sans décision."
    )


def test_each_event_keeps_its_routing() -> None:
    for event_type, expected in GOLDEN.items():
        assert EVENT_CATALOG[event_type].aggregate == expected, (
            f"Routage modifié pour {event_type!r}"
        )


def test_every_entry_is_a_behavior() -> None:
    assert all(isinstance(b, EventBehavior) for b in EVENT_CATALOG.values())


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


def test_every_count_carrying_event_is_in_the_catalog() -> None:
    # Un porteur de cardinalité qui ne serait pas au catalogue serait routé par le
    # défaut : contrat à moitié déclaré, l'exact travers que F15 ferme.
    assert COUNT_CARRYING_EVENTS <= set(EVENT_CATALOG)
