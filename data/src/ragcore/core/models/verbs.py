"""Le type pydantic d'un verbe de relation — la frontière entre une chaîne et un schéma.

**Pourquoi ce module existe, et pourquoi ici.** Le verbe d'une arête est défini par
``core/links/vocabulary.py`` : c'est lui qui dit ce qu'est un verbe et qui nomme ceux
que le domaine connaît. Mais ``core/models`` ne peut pas importer ``core/links`` — c'est
``links`` qui dépend des modèles (il fabrique des ``Relation``), et l'inverse ferait un
cycle.

Ce module porte donc la seule chose dont les modèles ont besoin : **la validation**. La
règle de forme y est définie une fois, et ``vocabulary.py`` la réexporte. Il n'y a pas
deux vérités sur ce qu'est un verbe valide — il y en a une, et deux portes d'entrée.

**Ce que la validation protège.** Le verbe devient un **type d'arête Neo4j**
(``MERGE (a)-[r:$(verb)]->(b)``). Une chaîne avec un espace, un guillemet ou un
caractère de contrôle produirait un type intraversable — ou, dans une requête construite
par concaténation, une injection. Un ``RelationVerb`` qui a franchi ce type est *par
construction* sûr à écrire dans le graphe : la sûreté est une propriété du type, pas une
discipline de l'appelant.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator

__all__ = ["VERB_PATTERN", "ValidatedVerb", "normalize_verb"]

VERB_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
"""La forme d'un verbe : minuscules, chiffres, tirets bas. Rien d'autre."""


def normalize_verb(raw: str) -> str:
    """Normalise et valide un verbe. Lève ``ValueError`` s'il ne peut pas en être un.

    La normalisation (``strip`` + minuscules) est faite **avant** la validation, et pas
    après : ``"CITATION"`` et ``"citation"`` sont le même verbe, et le graphe ne doit pas
    porter deux types d'arête pour un seul fait. Un verbe est un mot, pas une casse.
    """
    candidate = raw.strip().lower()
    if not VERB_PATTERN.match(candidate):
        msg = (
            f"Verbe de relation invalide : {raw!r}. Un verbe devient un type d'arête "
            f"Neo4j ; il doit matcher {VERB_PATTERN.pattern}."
        )
        raise ValueError(msg)
    return candidate


ValidatedVerb = Annotated[str, AfterValidator(normalize_verb)]
"""Un verbe validé, utilisable comme champ pydantic.

Une ``Relation`` construite avec ``relation_type="ZORGLUB"`` porte ``"zorglub"`` : la
normalisation a lieu à la frontière du modèle, donc **avant** toute écriture en base.
Une ``Relation`` construite avec ``relation_type="a b"`` ne se construit pas.
"""
