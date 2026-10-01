"""Cliquet : les ``typelien`` que LEGI déclare réellement. Retirer une entrée ferait
entrer toute une famille d'arêtes sous son nom brut. Un typelien nouveau ne fait pas
échouer ce test : il ressort au bilan du run.
"""

from ragcore.core.links import CITES
from ragcore.sources.legislatif.vocabulary import TYPELIEN_TO_VERB

TYPELIENS = {
    "CITATION",
    "TXT_SOURCE",
    "MODIFIE",
    "CODIFICATION",
    "CONCORDANCE",
    "MODIFICATION",
    "CONCORDE",
    "SPEC_APPLI",
    "CREATION",
    "CREE",
    "APPLICATION",
    "ABROGE",
    "TXT_ASSOCIE",
    "TRANSFERT",
    "DEPLACE",
    "ABROGATION",
}


def test_les_seize_typeliens_du_corpus_sont_couverts() -> None:
    """Mesuré sur le corpus LEGI."""
    assert set(TYPELIEN_TO_VERB) == TYPELIENS


def test_les_paires_actives_et_passives_partagent_leur_verbe() -> None:
    """MODIFIE et MODIFICATION sont le même verbe vu de ses deux bouts : ``sens`` porte
    la différence."""
    assert TYPELIEN_TO_VERB["MODIFIE"] == TYPELIEN_TO_VERB["MODIFICATION"]
    assert TYPELIEN_TO_VERB["CREE"] == TYPELIEN_TO_VERB["CREATION"]
    assert TYPELIEN_TO_VERB["ABROGE"] == TYPELIEN_TO_VERB["ABROGATION"]
    assert TYPELIEN_TO_VERB["CONCORDE"] == TYPELIEN_TO_VERB["CONCORDANCE"]


def test_la_citation_est_le_verbe_dominant() -> None:
    """88 % des liens du corpus."""
    assert TYPELIEN_TO_VERB["CITATION"] == CITES
