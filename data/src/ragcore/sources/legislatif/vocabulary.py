"""Le vocabulaire de liens de LEGI et sa traduction vers le domaine, pour que le reste
du code n'ait jamais à connaître le mot ``CODIFICATION``.

Pas un filtre : un ``typelien`` absent entre sous son nom brut et remonte au bilan.
"""

from ragcore.core.links import (
    ABROGE,
    APPLIQUE,
    APPLIQUE_SPEC,
    ASSOCIE,
    CITE,
    CODIFIE,
    CONCORDE,
    CREE,
    DEPLACE,
    MODIFIE,
    SOURCE,
    TRANSFERE,
    LinkTable,
    RelationVerb,
)

__all__ = ["LEGI_LINK_TABLE", "TYPELIEN_TO_VERB"]


TYPELIEN_TO_VERB: dict[str, RelationVerb] = {
    # MODIFIE et MODIFICATION sont le même verbe vu de ses deux bouts : c'est `sens`,
    # pas le typelien, qui oriente l'arête. Les nombres sont les liens du corpus.
    "CITATION": CITE,  # 14 326
    "MODIFIE": MODIFIE,  # 262
    "MODIFICATION": MODIFIE,  # 134
    "ABROGE": ABROGE,  # 3
    "ABROGATION": ABROGE,  # 1
    "CREE": CREE,  # 23
    "CREATION": CREE,  # 31
    "TXT_SOURCE": SOURCE,  # 961
    "CODIFICATION": CODIFIE,  # 176
    "CONCORDANCE": CONCORDE,  # 151
    "CONCORDE": CONCORDE,  # 109
    "SPEC_APPLI": APPLIQUE_SPEC,  # 39
    "APPLICATION": APPLIQUE,  # 6
    "TXT_ASSOCIE": ASSOCIE,  # 2
    "TRANSFERT": TRANSFERE,  # 2
    "DEPLACE": DEPLACE,  # 1
}
"""Les ``typelien`` mesurés sur le corpus (16 227 liens)."""


LEGI_LINK_TABLE = LinkTable(
    translation=TYPELIEN_TO_VERB,
    structural_kinds=frozenset({"LIEN_ART", "LIEN_SECTION_TA"}),
    ancestor_kinds=frozenset({"TITRE_TXT", "TITRE_TM"}),
)
"""Liens structurels et ancêtres donnent ``CONTIENT``, déduit de la forme du lien :
aucun ``typelien`` ne le porte."""
