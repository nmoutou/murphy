"""``core/links`` — le module hégémonique des liens. Deux faces, un vocabulaire.

Un seul module au cœur définit tout ce qui touche aux arêtes :

- **face extraction** (``extraction.py``) : une balise brute devient une ``Relation``.
  Appelée par le parser, jamais l'inverse.
- **face résolution** (phase 2) : une cible absente devient une arête, plus tard.

Elles partagent le vocabulaire de ``vocabulary.py``. **Personne d'autre ne fabrique de
lien** — c'est cette règle qui a manqué quand ``sources/legi/relations.py`` avait sa
propre notion d'orientation et sa propre table, et que 16 227 liens ont disparu sans
que le domaine s'en aperçoive.
"""

from .extraction import ExtractedLinks, LinkTable, extract_links
from .vocabulary import (
    ABROGATES,
    CANONICAL_VERBS,
    CITES,
    CONTAINS,
    CREATES,
    MODIFIES,
    REFERENCES,
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
    "MODIFIES",
    "REFERENCES",
    "ExtractedLinks",
    "LinkTable",
    "RelationVerb",
    "TranslationTable",
    "extract_links",
    "is_valid_verb",
    "translate",
    "verb",
]
