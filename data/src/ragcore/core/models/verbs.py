"""Le type pydantic d'un verbe de relation.

Il vit ici, et ``core/links/vocabulary.py`` le réexporte : ``links`` dépend des modèles,
l'inverse ferait un cycle.

Le verbe devient un type d'arête Neo4j : un espace, un guillemet ou un caractère de
contrôle donnerait un type intraversable, voire une injection. Un verbe qui a franchi ce
type est sûr à écrire dans le graphe par construction.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator

__all__ = ["VERB_PATTERN", "ValidatedVerb", "normalize_verb"]

VERB_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def normalize_verb(raw: str) -> str:
    """Lève ``ValueError`` si ``raw`` ne peut pas être un verbe.

    Normalisé avant validation : ``"CITATION"`` et ``"citation"`` sont le même verbe, le
    graphe ne doit pas porter deux types d'arête pour un seul fait.
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
"""Normalisé à la frontière du modèle, donc avant toute écriture : ``"ZORGLUB"`` devient
``"zorglub"``, ``"a b"`` lève."""
