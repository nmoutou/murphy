"""CLIQUET — la normalisation.

Ces valeurs sont écrites en base : un identifiant sérialisé, un nom de source,
une opération de manifest. Les changer, c'est rendre illisible ce qui est déjà
stocké. Le cliquet oblige à le faire sciemment.
"""

import pytest

from ragcore.core.links import CANONICAL_VERBS, translate, verb
from ragcore.core.models.enums import Operation, SourceName, TargetStore
from ragcore.core.models.identifiers import ELI, JorfId, UploadId
from ragcore.core.models.relation import Relation
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_INVALID_ELI,
    REASON_MISSING_CONTENT,
    REASON_NO_ELI,
    REASON_PARSE_ERROR,
    REASON_UNREADABLE,
    REASON_VALIDATION_ERROR,
)
from ragcore.core.services.unknown_categories import (
    CATEGORY_ROOT,
    CATEGORY_SENS,
    CATEGORY_TAG,
    CATEGORY_TYPELIEN,
)

SOURCE_NAMES = {
    "legi", "jorf", "upload",
    "capp", "cass", "inca", "jade", "constit",   # les cinq juri
}
OPERATIONS = {"insert", "update", "delete", "excluded"}
TARGET_STORES = {"mongo", "neo4j", "qdrant"}
EXCLUSION_REASONS = {
    "no_eli", "invalid_eli_format",
    "parse_error", "validation_error", "missing_content",
    "export_artifact",
    # Un XML qui ne parse pas : exclusion de LECTURE, distincte du `parse_error` qui est un
    # échec d'INTERPRÉTATION. Les confondre masquerait une source corrompue derrière un bug
    # supposé du parser.
    "unreadable",
}
UNKNOWN_CATEGORIES = {"typelien", "sens", "balise", "racine"}


def test_identifiers_serialize_with_their_kind() -> None:
    assert ELI(raw="LEGIARTI000006419264").serialize() == "eli:LEGIARTI000006419264"
    assert JorfId(raw="JORFTEXT000000465978").serialize() == "jorf:JORFTEXT000000465978"
    assert UploadId(raw="abc123").serialize() == "upload:abc123"


def test_source_names_are_frozen() -> None:
    assert {s.value for s in SourceName} == SOURCE_NAMES


def test_operations_are_frozen() -> None:
    assert {o.value for o in Operation} == OPERATIONS


def test_target_stores_are_frozen() -> None:
    assert {t.value for t in TargetStore} == TARGET_STORES


def test_exclusion_reasons_are_frozen() -> None:
    declared = {
        REASON_NO_ELI,
        REASON_INVALID_ELI,
        REASON_PARSE_ERROR,
        REASON_VALIDATION_ERROR,
        REASON_MISSING_CONTENT,
        REASON_EXPORT_ARTIFACT,
        REASON_UNREADABLE,
    }
    assert declared == EXCLUSION_REASONS


def test_unknown_categories_are_frozen() -> None:
    """Une catégorie d'inconnu qui n'est pas déclarée ici n'existe pas. Sans ce
    cliquet, chaque site d'émission inventerait sa chaîne et ``RunStats.unknowns``
    deviendrait illisible — des catégories jumelles qu'on ne saurait plus fusionner.
    """
    declared = {CATEGORY_TYPELIEN, CATEGORY_SENS, CATEGORY_TAG, CATEGORY_ROOT}
    assert declared == UNKNOWN_CATEGORIES


def test_canonical_verbs_are_frozen() -> None:
    """Les verbes que le DOMAINE sait nommer. Figés — ils sont écrits en base.

    Ce cliquet a changé de nature avec l'ouverture du vocabulaire, et c'est important
    de dire en quoi. Il figeait les membres d'un enum : la liste des verbes *autorisés*.
    Il fige désormais les verbes *canoniques* : ceux dont le domaine connaît la
    sémantique. Ce n'est plus une clôture, c'est un noyau.

    Ce qu'il protège n'a pas changé : ces six chaînes sont des **types d'arête Neo4j
    déjà écrits**. Les renommer rendrait illisible le graphe existant. Le cliquet oblige
    à le faire sciemment.

    Ce qu'il ne dit PLUS : que ce sont les seuls verbes possibles. Un mot de source non
    traduit entre dans le graphe sous son nom brut — c'est l'objet du test suivant.
    """
    assert set(CANONICAL_VERBS) == {
        "cites",
        "modifies",
        "abrogates",
        "creates",
        "contains",
        "references",
    }


def test_an_unknown_verb_enters_the_graph_instead_of_vanishing() -> None:
    """LE test du lot : un verbe inconnu produit une ARÊTE, pas un vide.

    C'est le contrat que l'ancien code ne tenait pas. Il *déclarait* l'inconnu
    (``unknowns``) puis faisait ``return None`` : l'arête disparaissait quand même. Le
    fil rouge nommait le trou au lieu de le boucher.

    ``translate`` rend ``(verbe, connu=False)`` : le mot entre **tel quel**, et
    l'appelant le déclare. Le graphe porte une arête vraie et un aveu — jamais un vide.
    """
    translated, known = translate({"CITATION": "cites"}, "ZORGLUB")

    assert translated == "zorglub", "le mot brut entre, normalisé"
    assert known is False, "et il est signalé comme non traduit"
    assert translated not in CANONICAL_VERBS, "sans polluer le vocabulaire du domaine"


def test_a_verb_that_cannot_be_an_edge_type_is_refused() -> None:
    """La seule chose qui n'entre pas : ce qui ne peut pas ÊTRE un type d'arête.

    Le verbe devient un type d'arête Cypher (``MERGE (a)-[r:$(verb)]->(b)``). La sûreté
    de cette requête ne vient pas d'un échappement : elle vient du TYPE. Une chaîne avec
    un espace, un guillemet ou un point-virgule ne peut pas franchir ``verb()`` — il n'y
    a donc rien à injecter, par construction.

    Refuser n'est pas jeter : il n'y a aucun mot sous une chaîne vide. On ne fabrique pas
    une arête à partir de rien.
    """
    for hostile in ("", "   ", "a b", "DROP;--", "arête", "1cites"):
        with pytest.raises(ValueError, match="Verbe de relation invalide"):
            verb(hostile)


def test_a_relation_normalizes_its_verb_at_the_model_boundary() -> None:
    """La normalisation a lieu AVANT toute écriture en base — dans le modèle lui-même.

    ``"CITATION"`` et ``"citation"`` sont le même verbe : le graphe ne doit pas porter
    deux types d'arête pour un seul fait. Le champ est un ``ValidatedVerb``, donc la
    ``Relation`` ne *peut pas* exister avec un verbe mal formé.
    """
    relation = Relation(
        source_identifier=ELI(raw="LEGIARTI000006419264"),
        target_identifier=ELI(raw="LEGIARTI000006419265"),
        relation_type="ZORGLUB",
        owner_id="tenant",
        source=SourceName.LEGI,
    )
    assert relation.relation_type == "zorglub"

    with pytest.raises(ValueError, match="Verbe de relation invalide"):
        Relation(
            source_identifier=ELI(raw="LEGIARTI000006419264"),
            target_identifier=ELI(raw="LEGIARTI000006419265"),
            relation_type="a b",
            owner_id="tenant",
            source=SourceName.LEGI,
        )
