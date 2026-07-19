"""``Hit`` — un résultat brut de recherche Qdrant, avant traduction en run.

DTO d'infra volontairement minimal : les trois champs que la baseline lit du
payload d'ingestion. ``identifier`` est l'identité canonique du document parent
sérialisée ``"<kind>:<raw>"`` (ADR-018) — elle devient ``RunEntry.doc_id`` sans
transformation. On ne modélise pas tout le payload : le harnais ne consomme que
ce dont il a besoin pour bâtir un run.
"""

from __future__ import annotations

from murphy_eval.core.models._base import Frozen


class Hit(Frozen):
    """Un point Qdrant remonté par une recherche : chunk, doc parent, score."""

    chunk_id: str
    identifier: str
    """Le ``doc_id`` canonique (ADR-018), lu du payload ``identifier``."""
    score: float
