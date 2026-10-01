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
    ABROGATES,
    CANONICAL_VERBS,
    CITES,
    CONTAINS,
    CREATES,
    MODIFIES,
    REFERENCES,
    SUCCEEDED_BY,
    RelationVerb,
    TranslationTable,
    is_valid_verb,
    translate,
    verb,
)

__all__ = [
    "ABROGATES",
    "CANONICAL_VERBS",
    "CITES",
    "CONTAINS",
    "CREATES",
    "HEURISTIC_KIND",
    "MODIFIES",
    "REFERENCES",
    "STILLBORN_SUFFIX",
    "SUCCEEDED_BY",
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
