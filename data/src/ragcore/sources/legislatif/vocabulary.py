"""Le vocabulaire de liens de LEGI et sa traduction vers le domaine, pour que le reste
du code n'ait jamais à connaître le mot ``CODIFICATION``.

Pas un filtre : un ``typelien`` absent entre sous son nom brut et remonte au bilan.
"""

from ragcore.core.links import (
    ABROGATES,
    CITES,
    CREATES,
    MODIFIES,
    REFERENCES,
    LinkTable,
    RelationVerb,
)

__all__ = ["LEGI_LINK_TABLE", "TYPELIEN_TO_VERB"]


TYPELIEN_TO_VERB: dict[str, RelationVerb] = {
    # MODIFIE et MODIFICATION sont le même verbe vu de ses deux bouts : c'est `sens`,
    # pas le typelien, qui oriente l'arête. Les nombres sont les liens du corpus.
    "CITATION": CITES,  # 14 326
    "MODIFIE": MODIFIES,  # 262
    "MODIFICATION": MODIFIES,  # 134
    "ABROGE": ABROGATES,  # 3
    "ABROGATION": ABROGATES,  # 1
    "CREE": CREATES,  # 23
    "CREATION": CREATES,  # 31
    # Sans sémantique distincte établie, rangés sciemment en renvois qualifiés : le
    # typelien d'origine survit dans metadata. Retirés d'ici, ils entreraient sous leur
    # nom brut.
    "TXT_SOURCE": REFERENCES,  # 961
    "CODIFICATION": REFERENCES,  # 176
    "CONCORDANCE": REFERENCES,  # 151
    "CONCORDE": REFERENCES,  # 109
    "SPEC_APPLI": REFERENCES,  # 39
    "APPLICATION": REFERENCES,  # 6
    "TXT_ASSOCIE": REFERENCES,  # 2
    "TRANSFERT": REFERENCES,  # 2
    "DEPLACE": REFERENCES,  # 1
}
"""Les ``typelien`` mesurés sur le corpus (16 227 liens)."""


LEGI_LINK_TABLE = LinkTable(
    translation=TYPELIEN_TO_VERB,
    structural_kinds=frozenset({"LIEN_ART", "LIEN_SECTION_TA"}),
    ancestor_kinds=frozenset({"TITRE_TXT", "TITRE_TM"}),
)
"""Liens structurels et ancêtres donnent ``CONTAINS``, déduit de la forme du lien :
aucun ``typelien`` ne le porte."""
