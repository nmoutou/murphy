"""Le vocabulaire de LEGI — et sa traduction vers le domaine. **Une table, pas du code.**

Ce module est la frontière entre ce que LEGI *dit* et ce que le domaine *sait*. Il existe
pour que le reste du code n'ait jamais à connaître le mot ``CODIFICATION``.

**Ce qu'il ne fait pas.** Il ne fait pas entrer les 16 mots de LEGI dans le vocabulaire du
domaine. Les verbes canoniques (``core/links/vocabulary.py``) sont partagés avec JORF et
la jurisprudence ; cette table-ci est la source. Les confondre, c'est laisser le
vocabulaire d'un fournisseur coloniser le langage commun.

**Ce qui a changé, et c'est le cœur du lot.** Un ``typelien`` absent de cette table ne
disparaît plus. ``core/links.translate`` le fait entrer dans le graphe **sous son nom
brut**, et le déclare dans ``unknowns``. La table n'est donc plus un filtre : c'est un
*dictionnaire de traduction*. Ce qu'elle ignore passe quand même la frontière — en
version originale, et avec une note.
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
    # Le verbe est toujours nommé DU POINT DE VUE DE LA SOURCE de l'arête. C'est
    # pourquoi MODIFIE et MODIFICATION sont le MÊME verbe : ce ne sont pas deux
    # relations, c'est une relation vue de ses deux bouts. L'attribut `sens` dit de
    # quel bout on la regarde — et c'est lui, pas le typelien, qui l'oriente.
    "CITATION": CITES,  # 14 326 — l'écrasante majorité
    "MODIFIE": MODIFIES,  # 262
    "MODIFICATION": MODIFIES,  # 134
    "ABROGE": ABROGATES,  # 3
    "ABROGATION": ABROGATES,  # 1
    "CREE": CREATES,  # 23
    "CREATION": CREATES,  # 31
    # Faute de sémantique distincte ÉTABLIE, ces liens sont des renvois qualifiés : le
    # verbe est REFERENCES, et le typelien d'origine survit dans metadata.
    #
    # **C'est un choix, et il faut le distinguer de l'ingestion brute.** Depuis que le
    # vocabulaire est ouvert, ne PAS les mettre ici les ferait entrer sous leur nom
    # (`codification`, `concordance`…) — ce qui serait défendable. On préfère le
    # rangement explicite : ces neuf mots-là, on les a VUS et on a décidé qu'ils sont
    # des renvois. La table dit « je sais, et je range ici » ; l'ingestion brute dit
    # « je ne sais pas, et je le montre ». Les deux sont honnêtes, mais ce ne sont pas
    # les mêmes affirmations, et il ne faut pas les confondre.
    #
    # Le jour où « codification » aura un sens propre dans le domaine, il devient un
    # verbe canonique et cette ligne bouge d'un cran.
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
"""Les 16 ``typelien`` mesurés sur le corpus (16 227 liens). Exhaustive AUJOURD'HUI.

Elle ne prétend pas l'être demain — et depuis que le vocabulaire est ouvert, elle n'a
plus besoin de l'être : ce qu'elle ne contient pas entre sous son nom brut et remonte
dans ``unknowns``. Le corpus enseigne son vocabulaire ; la table apprend, sans que rien
ne soit perdu entre-temps.
"""


LEGI_LINK_TABLE = LinkTable(
    translation=TYPELIEN_TO_VERB,
    # Les liens structurels : ils n'ont NI typelien NI sens, parce que leur orientation
    # est connue par construction. Une section contient ses articles ; un texte contient
    # ses sections. Ce sens-là ne peut pas s'inverser.
    structural_kinds=frozenset({"LIEN_ART", "LIEN_SECTION_TA"}),
    # Les ancêtres déclarés par <CONTEXTE> : l'arête va de l'ancêtre VERS le document.
    # C'est la fermeture transitive de la contenance — d'où la réduction, en aval.
    ancestor_kinds=frozenset({"TITRE_TXT", "TITRE_TM"}),
)
"""Tout ce que LEGI déclare de ses liens, en UNE donnée.

C'est la forme que prend « une source nouvelle = une table ». **Il n'y a plus d'extracteur
LEGI du tout** : la mécanique (orienter, fabriquer, déclarer l'inconnu) vit dans
``core/links``, et LEGI n'apporte que son vocabulaire. La jurisprudence a apporté le sien
— et n'a pas écrit une ligne de code d'extraction.

Le verbe implicite des liens structurels et des ancêtres est ``CONTAINS`` : il n'a pas à
figurer dans la table de traduction, puisqu'aucun ``typelien`` ne le porte — il est déduit
de la *forme* du lien, pas de son vocabulaire.
"""
