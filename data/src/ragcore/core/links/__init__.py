"""Tout ce qui touche aux arêtes, et nulle part ailleurs.

- extraction (``extraction.py``) : une balise brute devient une ``Relation`` ; appelée
  par le parser, jamais l'inverse ;
- résolution (phase 2) : une cible absente devient une arête, plus tard.

Les deux partagent ``vocabulary.py``. Personne d'autre ne fabrique de lien.
"""

from .extraction import (
    HEURISTIC_KIND,
    STILLBORN_SUFFIX,
    VERSION_KIND,
    ExtractedLinks,
    LinkSubject,
    LinkTable,
    extract_links,
)
from .vocabulary import (
    ABROGE,
    APPLIQUE,
    APPLIQUE_SPEC,
    ASSOCIE,
    CANONICAL_VERBS,
    CITE,
    CODIFIE,
    CONCORDE,
    CONTIENT,
    CREE,
    DEPLACE,
    MODIFIE,
    SOURCE,
    SUIVI_PAR,
    TRANSFERE,
    RelationVerb,
    TranslationTable,
    is_valid_verb,
    translate,
    verb,
)

__all__ = [
    "ABROGE",
    "APPLIQUE",
    "APPLIQUE_SPEC",
    "ASSOCIE",
    "CANONICAL_VERBS",
    "CITE",
    "CODIFIE",
    "CONCORDE",
    "CONTIENT",
    "CREE",
    "DEPLACE",
    "HEURISTIC_KIND",
    "MODIFIE",
    "SOURCE",
    "STILLBORN_SUFFIX",
    "SUIVI_PAR",
    "TRANSFERE",
    "VERSION_KIND",
    "ExtractedLinks",
    "LinkSubject",
    "LinkTable",
    "RelationVerb",
    "TranslationTable",
    "extract_links",
    "is_valid_verb",
    "translate",
    "verb",
]
