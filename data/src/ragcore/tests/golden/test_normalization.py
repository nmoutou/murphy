"""Cliquet : les valeurs écrites en base (identifiants, noms de source, raisons
d'exclusion, verbes…). Les changer rendrait illisible ce qui est stocké : le cliquet
oblige à le faire sciemment.
"""

import pytest

from ragcore.core.links import CANONICAL_VERBS, translate, verb
from ragcore.core.models.enums import SourceName, TargetStore
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.relation import Relation
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_PARSE_ERROR,
    REASON_UNREADABLE,
    REASON_VALIDATION_ERROR,
)
from ragcore.core.services.unknown_categories import (
    CATEGORY_LINK,
    CATEGORY_ROOT,
    CATEGORY_TAG,
)

SOURCE_NAMES = {
    "legi",
    "jorf",
    "upload",
    "capp",
    "cass",
    "inca",
    "jade",
    "constit",  # les cinq juri
}
TARGET_STORES = {"mongo", "neo4j", "opensearch"}
EXCLUSION_REASONS = {
    "parse_error",
    "validation_error",
    "export_artifact",
    # Exclusion de lecture, distincte du `parse_error`, échec d'interprétation
    "unreadable",
}
# Trois catégories plates (ADR-024). Un lien qu'on ne sait pas écrire n'est pas un type :
# il est compté par `relation.unknown`.
UNKNOWN_CATEGORIES = {"tags", "roots", "links"}


def test_identifiers_serialize_as_their_raw_value() -> None:
    assert Identifier(raw="LEGIARTI000006419264").serialize() == "LEGIARTI000006419264"
    assert Identifier(raw="JORFTEXT000000465978").serialize() == "JORFTEXT000000465978"


def test_source_names_are_frozen() -> None:
    assert {s.value for s in SourceName} == SOURCE_NAMES


def test_target_stores_are_frozen() -> None:
    assert {t.value for t in TargetStore} == TARGET_STORES


def test_exclusion_reasons_are_frozen() -> None:
    declared = {
        REASON_PARSE_ERROR,
        REASON_VALIDATION_ERROR,
        REASON_EXPORT_ARTIFACT,
        REASON_UNREADABLE,
    }
    assert declared == EXCLUSION_REASONS


def test_unknown_categories_are_frozen() -> None:
    """Une catégorie qui n'est pas déclarée ici n'existe pas : sinon chaque site
    d'émission inventerait la sienne."""
    declared = {
        CATEGORY_TAG,
        CATEGORY_ROOT,
        CATEGORY_LINK,
    }
    assert declared == UNKNOWN_CATEGORIES


def test_canonical_verbs_are_frozen() -> None:
    """Les verbes canoniques, déjà écrits en base comme types d'arête Neo4j. Ce ne sont
    pas les seuls possibles : un mot non traduit entre sous son nom brut (test suivant).
    """
    assert set(CANONICAL_VERBS) == {
        "cite",
        "modifie",
        "abroge",
        "cree",
        "source",
        "codifie",
        "concorde",
        "applique_spec",
        "applique",
        "associe",
        "transfere",
        "deplace",
        "contient",
        # L'axe temporel : la chaîne des versions d'un article
        "suivi_par",
    }


def test_an_unknown_verb_enters_the_graph_instead_of_vanishing() -> None:
    """Un verbe inconnu produit une arête sous son nom brut, et l'appelant le déclare."""
    translated, known = translate({"CITATION": "cite"}, "ZORGLUB")

    assert translated == "zorglub", "le mot brut entre, normalisé"
    assert known is False, "et il est signalé comme non traduit"
    assert translated not in CANONICAL_VERBS, "sans polluer le vocabulaire du domaine"


def test_a_verb_that_cannot_be_an_edge_type_is_refused() -> None:
    """Seul ce qui ne peut pas être un type d'arête n'entre pas : la sûreté de la
    requête Cypher vient du type, pas d'un échappement."""
    for hostile in ("", "   ", "a b", "DROP;--", "arête", "1cites"):
        with pytest.raises(ValueError, match="Verbe de relation invalide"):
            verb(hostile)


def test_a_relation_normalizes_its_verb_at_the_model_boundary() -> None:
    """Normalisé dans le modèle, avant toute écriture : ``"CITATION"`` et ``"citation"``
    sont le même verbe."""
    relation = Relation(
        source_identifier=Identifier(raw="LEGIARTI000006419264"),
        target_identifier=Identifier(raw="LEGIARTI000006419265"),
        relation_type="ZORGLUB",
        source=SourceName.LEGI,
    )
    assert relation.relation_type == "zorglub"

    with pytest.raises(ValueError, match="Verbe de relation invalide"):
        Relation(
            source_identifier=Identifier(raw="LEGIARTI000006419264"),
            target_identifier=Identifier(raw="LEGIARTI000006419265"),
            relation_type="a b",
            source=SourceName.LEGI,
        )
