"""Le verbe d'une arête, et la traduction qui ne jette jamais rien.

Le verbe est une chaîne validée, pas un enum : le domaine ne peut pas connaître
d'avance tout ce que six sources vont dire. Il nomme les verbes qu'il sait
interpréter ; un autre entre sous son nom brut et remonte au bilan. Le graphe porte
donc une arête vraie plutôt qu'un vide, et le serving doit filtrer sur les verbes
qu'il connaît.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NewType

from ..models.verbs import VERB_PATTERN, normalize_verb

__all__ = [
    "ABROGATES",
    "CANONICAL_VERBS",
    "CITES",
    "CONTAINS",
    "CREATES",
    "MODIFIES",
    "REFERENCES",
    "SUCCEEDED_BY",
    "RelationVerb",
    "TranslationTable",
    "is_valid_verb",
    "translate",
    "verb",
]

RelationVerb = NewType("RelationVerb", str)
"""Toujours nommé du point de vue de la source de l'arête : ``MODIFIE`` et
``MODIFICATION`` sont le même verbe, vu de ses deux bouts ; ``sens`` dit lequel.
"""


# ── Ce que le domaine sait nommer ───────────────────────────────────────────────
#
# Des constantes, pas un enum : des noms privilégiés dans un espace ouvert.

CITES = RelationVerb("cites")
MODIFIES = RelationVerb("modifies")
ABROGATES = RelationVerb("abrogates")
CREATES = RelationVerb("creates")

CONTAINS = RelationVerb("contains")
"""Contenance structurelle : un texte contient ses sections, une section ses articles.

Le seul verbe transitif, donc le seul réductible (``core/services/relation_reduction``).
Son orientation est connue par construction, jamais lue dans ``sens``.
"""

REFERENCES = RelationVerb("references")
"""Le renvoi qualifié : un verbe de source sans sémantique propre dans le domaine, rangé
ici sciemment par une table de traduction. À ne pas confondre avec le verbe brut d'un
``typelien`` inconnu.
"""

SUCCEEDED_BY = RelationVerb("succeeded_by")
"""L'axe temporel : ``(v1)-[:succeeded_by]->(v2)``, dans le sens du temps.

Ni une contenance (la réduire détruirait la ligne de vie), ni une citation. Le graphe
porte la chaîne des versions d'un article, pas leur produit cartésien. Une version
mort-née est hors chaîne, en branche latérale ; l'``etat`` sur l'arête permet de
l'écarter.
"""

CANONICAL_VERBS: frozenset[RelationVerb] = frozenset(
    {CITES, MODIFIES, ABROGATES, CREATES, CONTAINS, REFERENCES, SUCCEEDED_BY}
)
"""Les verbes dont le domaine connaît la sémantique, figés par un cliquet : ils sont
écrits en base. Pas une validation : un verbe hors de cet ensemble reste légitime.
"""


TranslationTable = Mapping[str, RelationVerb]
"""Le vocabulaire d'une source vers celui du domaine. Elle vit dans ``sources/<nom>/``,
jamais ici : le domaine ne doit pas savoir que LEGI dit ``CODIFICATION``.
"""


def verb(raw: str) -> RelationVerb:
    """Lève ``ValueError`` si la chaîne ne peut pas être un type d'arête Neo4j."""
    return RelationVerb(normalize_verb(raw))


def is_valid_verb(raw: str) -> bool:
    """Sans lever."""
    return bool(VERB_PATTERN.match(raw.strip().lower()))


def translate(table: TranslationTable, raw: str) -> tuple[RelationVerb | None, bool]:
    """Rend ``(verbe, connu)`` :

    - ``connu=True`` : la table a traduit ;
    - ``connu=False`` : le verbe est le mot brut, en minuscules, et l'arête existe
      quand même ;
    - ``(None, False)`` : le mot ne peut pas être un verbe (vide, caractères interdits).

    C'est l'appelant qui déclare l'inconnu à la télémétrie : la fonction reste pure.
    """
    known = table.get(raw)
    if known is not None:
        return known, True

    if not is_valid_verb(raw):
        return None, False

    return verb(raw), False
