"""``Run`` — la sortie ordonnée d'une config de récupération, niveau chunk.

Contrat unique de P2→P3 (ADR-016) : une config, quelle que soit sa mécanique
interne (vectoriel, graphe, hybride), expose `requête → liste ordonnée d'IDs
canoniques (+ scores)`. Ce module modélise cette sortie une fois traduite par
l'adapter (B-05) — le scorer ne connaît que ce contrat, jamais le pipeline qui
l'a produit.

**Couture B-05** : `doc_id` est un champ requis sur `RunEntry`, alors qu'une
ligne TREC plate ne porte que `chunk_id`. En production, B-05 émet directement
des runs JSONL canoniques portant `doc_id` par chunk (résolu depuis sa propre
connaissance du corpus) ; le loader TREC plat (``adapters/trec/projection.py``)
n'a besoin d'un résolveur que pour des runs externes déjà en forme plate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RunEntry(_Frozen):
    """Une ligne de run : un chunk, son rang et son score pour une requête."""

    query_id: str
    chunk_id: str
    doc_id: str
    rank: int = Field(ge=1)
    score: float
    run_tag: str = ""


class Run(_Frozen):
    """L'ensemble des lignes produites par une config, sur toutes les requêtes."""

    entries: tuple[RunEntry, ...]
    run_tag: str = ""

    def by_query(self) -> dict[str, list[RunEntry]]:
        """Groupe les entrées par requête, dans l'ordre d'apparition."""
        grouped: dict[str, list[RunEntry]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.query_id, []).append(entry)
        return grouped
