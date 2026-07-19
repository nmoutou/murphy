"""Vues niveau document — la sortie de l'agrégation chunk→document (ADR-006).

Un seul jeu de qrels au niveau chunk produit deux familles de métriques :
passage et document. `DocQrels`/`DocRun` sont la forme intermédiaire commune
que consomment le nDCG@R maison, les diagnostics maison et `ranx`. Elles ne
sont **jamais** construites directement depuis une requête utilisateur — elles
sortent exclusivement de ``core/services/aggregation.py``.

Représentation en tuple de paires triées (et non ``dict``) pour rester
gelées : un ``dict`` mutable n'a pas sa place dans un modèle ``frozen=True``,
et le tri fixe un ordre déterministe indépendant de l'ordre de construction —
même discipline que ``canonicalize()`` côté ``ragcore``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DocQrels(_Frozen):
    """Grades de pertinence au niveau document, pour une requête (max des chunks)."""

    query_id: str
    doc_grades: tuple[tuple[str, int], ...]
    """``(doc_id, grade)``, trié par ``doc_id`` croissant."""

    def as_dict(self) -> dict[str, int]:
        return dict(self.doc_grades)


class DocRun(_Frozen):
    """Rangs au niveau document, pour une requête (rang du premier chunk)."""

    query_id: str
    doc_ranks: tuple[tuple[str, int], ...]
    """``(doc_id, rang)``, dans l'ordre de rang croissant (1..n, densifié)."""

    def as_dict(self) -> dict[str, int]:
        return dict(self.doc_ranks)

    def ranked_doc_ids(self) -> list[str]:
        """Les ``doc_id`` dans l'ordre de rang croissant."""
        return [doc_id for doc_id, _rank in self.doc_ranks]
