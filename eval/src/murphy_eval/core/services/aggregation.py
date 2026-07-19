"""Agrégation chunk→document (ADR-006) — MAISON, appliquée avant tout scoring.

Deux règles, arrêtées et non négociables :

- **qrels** : le grade d'un document est le **max** des grades de ses chunks.
  Pas de biais de taille — un document en 40 chunks ne l'emporte pas sur un
  document en 2 chunks par simple accumulation.
- **runs** : le rang d'un document est le rang de son **premier chunk**
  rencontré (le plus proche de la tête de liste). Les chunks suivants du même
  document sont ignorés — ADR-006 : « les fusions de scores sophistiquées
  sont des stratégies de config évaluées, jamais des règles du harnais ».

Cette agrégation est la seule intelligence que le scorer maison porte sur les
runs ; tout le reste (nDCG@R, diagnostics) opère ensuite sur des vues 100 %
niveau document. **Aucune métrique n'est jamais calculée au niveau chunk**
(E-P2-03) : c'est ici, et seulement ici, que le passage se fait.

Départage déterministe (cas d'égalité de score/rang à l'entrée) : l'ordre
d'apparition dans la séquence d'entrée, puis ``chunk_id`` croissant. Priorité
au déterminisme sur toute autre considération (`CADRAGE_evaluation` §10) —
deux appels sur la même entrée doivent produire des modèles byte-identiques.
"""

from __future__ import annotations

from murphy_eval.core.models.aggregated import DocQrels, DocRun
from murphy_eval.core.models.judgment import Qrels
from murphy_eval.core.models.run import Run, RunEntry


def aggregate_qrels(qrels: Qrels) -> dict[str, DocQrels]:
    """Un ``DocQrels`` par requête : grade document = max des grades chunk."""
    result: dict[str, DocQrels] = {}
    for query_id, judgments in qrels.by_query().items():
        best_grade: dict[str, int] = {}
        for judgment in judgments:
            current = best_grade.get(judgment.doc_id)
            if current is None or judgment.grade > current:
                best_grade[judgment.doc_id] = judgment.grade
        ordered = tuple(sorted(best_grade.items()))
        result[query_id] = DocQrels(query_id=query_id, doc_grades=ordered)
    return result


def aggregate_run(run: Run) -> dict[str, DocRun]:
    """Un ``DocRun`` par requête : rang document = rang du premier chunk vu.

    Les entrées sont d'abord remises en ordre de rang croissant (puis
    ``chunk_id`` croissant pour départager une égalité de rang), afin que le
    résultat ne dépende jamais de l'ordre d'arrivée des lignes en entrée —
    seul le rang qu'elles portent compte.
    """
    result: dict[str, DocRun] = {}
    for query_id, entries in run.by_query().items():
        ordered_entries = sorted(entries, key=_rank_then_chunk_id)
        first_rank: dict[str, int] = {}
        for entry in ordered_entries:
            if entry.doc_id not in first_rank:
                first_rank[entry.doc_id] = entry.rank
        # Densification : l'ordre relatif (par rang de premier chunk, puis
        # doc_id pour départager une égalité) devient 1..n contigu, sans trou
        # laissé par les rangs de chunks consommés par un doc déjà vu.
        densified = tuple(
            (doc_id, position)
            for position, (doc_id, _rank) in enumerate(
                sorted(first_rank.items(), key=lambda item: (item[1], item[0])),
                start=1,
            )
        )
        result[query_id] = DocRun(query_id=query_id, doc_ranks=densified)
    return result


def _rank_then_chunk_id(entry: RunEntry) -> tuple[int, str]:
    return (entry.rank, entry.chunk_id)
