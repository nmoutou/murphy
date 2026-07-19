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

from pydantic import model_validator

from murphy_eval.core.models._base import Frozen


class DocQrels(Frozen):
    """Grades de pertinence au niveau document, pour une requête (max des chunks)."""

    query_id: str
    doc_grades: tuple[tuple[str, int], ...]
    """``(doc_id, grade)``, trié par ``doc_id`` croissant."""

    def as_dict(self) -> dict[str, int]:
        return dict(self.doc_grades)


class DocRun(Frozen):
    """Rangs au niveau document, pour une requête (rang du premier chunk)."""

    query_id: str
    doc_ranks: tuple[tuple[str, int], ...]
    """``(doc_id, rang)`` **densifiés** : rangs = ``1..n`` exactement, stricte-
    ment croissants, sans trou ni ex æquo, et ``doc_id`` sans doublon.

    Cet invariant n'est pas décoratif : il est **consommé** en aval. En
    particulier ``diagnostics._rank_to_score`` traduit chaque rang en score
    ``1/rang`` pour que le tri interne de ``ranx`` (MAP, Doc-MRR) reproduise
    exactement cet ordre — ce qui n'est fidèle que si l'ordre des rangs est
    *total* (aucun ex æquo à départager par ``ranx`` à notre place). Le
    validateur ci-dessous le garantit à la construction, quel que soit le
    producteur (``aggregate_run`` aujourd'hui, un adapter B-05 demain).
    """

    @model_validator(mode="after")
    def _ranks_densifies(self) -> DocRun:
        ranks = [rank for _doc_id, rank in self.doc_ranks]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError(
                f"doc_ranks doit porter des rangs densifiés 1..n "
                f"(strictement croissants, sans trou ni ex æquo) ; reçu {ranks}"
            )
        doc_ids = [doc_id for doc_id, _rank in self.doc_ranks]
        if len(set(doc_ids)) != len(doc_ids):
            raise ValueError(f"doc_ranks ne doit porter aucun doublon de doc_id ; reçu {doc_ids}")
        return self

    def as_dict(self) -> dict[str, int]:
        return dict(self.doc_ranks)

    def ranked_doc_ids(self) -> list[str]:
        """Les ``doc_id`` dans l'ordre de rang croissant."""
        return [doc_id for doc_id, _rank in self.doc_ranks]
