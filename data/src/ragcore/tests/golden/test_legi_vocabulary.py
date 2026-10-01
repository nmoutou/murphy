"""CLIQUET — le vocabulaire de LEGI.

Ces 16 ``typelien`` sont ceux que le corpus déclare réellement (16 227 liens mesurés).
La table est ce qui les fait exister dans le graphe : en retirer une entrée, c'est
faire disparaître silencieusement une famille d'arêtes — exactement le bug que le
lot 4 corrige.

Le cliquet et l'instrument sont complémentaires : celui-ci FIGE ce qu'on connaît,
``unknowns`` DÉCOUVRE ce qu'on ne connaît pas. Un 17ᵉ typelien publié par LEGI ne
fera pas échouer ce test — il ressortira à l'exécution, dans le bilan du run.
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
    """Mesuré sur /mnt/data/Murphy/src/LEGI : ces 16 valeurs, et pas d'autres."""
    assert set(TYPELIEN_TO_VERB) == TYPELIENS


def test_les_paires_actives_et_passives_partagent_leur_verbe() -> None:
    """MODIFIE et MODIFICATION ne sont pas deux relations : c'est la même, vue de ses
    deux bouts. Les séparer en deux types serait dédoubler le graphe. C'est ``sens``
    qui porte la différence — l'orientation, pas le verbe.
    """
    assert TYPELIEN_TO_VERB["MODIFIE"] == TYPELIEN_TO_VERB["MODIFICATION"]
    assert TYPELIEN_TO_VERB["CREE"] == TYPELIEN_TO_VERB["CREATION"]
    assert TYPELIEN_TO_VERB["ABROGE"] == TYPELIEN_TO_VERB["ABROGATION"]
    assert TYPELIEN_TO_VERB["CONCORDE"] == TYPELIEN_TO_VERB["CONCORDANCE"]


def test_la_citation_est_le_verbe_dominant() -> None:
    """14 326 des 16 227 liens. Si celui-là se met à mal se traduire, c'est 88 % du
    graphe qui bascule sans qu'un test de couverture s'en aperçoive.
    """
    assert TYPELIEN_TO_VERB["CITATION"] == CITES
