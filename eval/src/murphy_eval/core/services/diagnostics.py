"""Diagnostics (ADR-007) : R-Precision, Recall@2R, Doc-Recall@R MAISON ;
MAP et Doc-MRR via ``ranx``.

Le partage suit ADR-027 à la lettre : « la coupe adaptative @R reste
maison ». R-Precision, Recall@2R et Doc-Recall@R ont toutes une coupe qui
dépend de R — donc de la requête — donc elles restent maison, en pure
arithmétique d'ensemble sur les vues déjà agrégées niveau document. MAP et
Doc-MRR n'ont **pas** de coupe (moyenne sur tout le classement, rang du
premier pertinent) : ce sont exactement les deux métriques que `ranx` calcule
nativement sans qu'on lui demande une coupe par requête, donc elles lui sont
déléguées telles quelles — surface `ranx` réduite au strict minimum, pas
d'appel par requête.

Toutes les entrées ici sont **déjà niveau document** (sorties de
``aggregation.py``) : aucune métrique n'est calculée au niveau chunk
(E-P2-03).
"""

from __future__ import annotations

from ranx import Qrels as RanxQrels
from ranx import Run as RanxRun
from ranx import evaluate

from murphy_eval.core.models.aggregated import DocQrels, DocRun


def r_precision(doc_grades: dict[str, int], ranked_doc_ids: list[str]) -> float:
    """Précision dans les R premiers documents (R = nb de pertinents)."""
    r = sum(1 for g in doc_grades.values() if g > 0)
    if r == 0:
        return 0.0
    top_r = ranked_doc_ids[:r]
    hits = sum(1 for doc_id in top_r if doc_grades.get(doc_id, 0) > 0)
    return hits / r


def recall_at_2r(doc_grades: dict[str, int], ranked_doc_ids: list[str]) -> float:
    """Rappel dans les 2R premiers documents (ADR-007 : profondeur en multiple de R)."""
    r = sum(1 for g in doc_grades.values() if g > 0)
    if r == 0:
        return 0.0
    top_2r = ranked_doc_ids[: 2 * r]
    hits = sum(1 for doc_id in top_2r if doc_grades.get(doc_id, 0) > 0)
    return hits / r


def doc_recall_at_r(doc_grades: dict[str, int], ranked_doc_ids: list[str]) -> float:
    """Rappel dans les R premiers documents."""
    r = sum(1 for g in doc_grades.values() if g > 0)
    if r == 0:
        return 0.0
    top_r = ranked_doc_ids[:r]
    hits = sum(1 for doc_id in top_r if doc_grades.get(doc_id, 0) > 0)
    return hits / r


def map_and_doc_mrr(
    doc_qrels: dict[str, DocQrels], doc_runs: dict[str, DocRun]
) -> dict[str, tuple[float, float]]:
    """MAP et Doc-MRR par requête, calculés par ``ranx`` (sans coupe).

    Retourne ``{query_id: (map, doc_mrr)}`` pour l'union des requêtes
    présentes dans les qrels ou le run. Une requête totalement absente d'un
    côté obtient un score de 0 — mais ``ranx.Run``/``ranx.Qrels`` lèvent une
    ``ValueError`` dès qu'**un seul** dict de documents est vide, y compris
    parmi d'autres requêtes non vides (bug de la bibliothèque sur ce cas
    limite, vérifié empiriquement). Ces requêtes sont donc écartées de
    l'appel `ranx` et scorées directement à ``(0.0, 0.0)`` : aucun document
    des deux côtés → MAP et MRR sont nuls par définition, ``ranx`` n'a rien à
    apprendre de plus.
    """
    all_query_ids = sorted(set(doc_qrels) | set(doc_runs))
    if not all_query_ids:
        return {}

    def _grades(qid: str) -> dict[str, int]:
        return doc_qrels[qid].as_dict() if qid in doc_qrels else {}

    def _scores(qid: str) -> dict[str, float]:
        return (
            {
                doc_id: _rank_to_score(rank)
                for doc_id, rank in doc_runs[qid].as_dict().items()
            }
            if qid in doc_runs
            else {}
        )

    computable_ids = [qid for qid in all_query_ids if _grades(qid) and _scores(qid)]
    degenerate_ids = [qid for qid in all_query_ids if qid not in computable_ids]

    results: dict[str, tuple[float, float]] = {
        qid: (0.0, 0.0) for qid in degenerate_ids
    }
    if not computable_ids:
        return results

    ranx_qrels = RanxQrels({qid: _grades(qid) for qid in computable_ids})
    ranx_run = RanxRun({qid: _scores(qid) for qid in computable_ids})

    ranx_results = evaluate(
        ranx_qrels, ranx_run, ["map", "mrr"], return_mean=False, make_comparable=True
    )
    # ranx trie les query_id en interne (numba typed dict) : l'ordre de sortie
    # des arrays est l'ordre trié, pas l'ordre d'insertion — jamais l'ordre
    # d'insertion des dicts Python ci-dessus.
    sorted_computable_ids = sorted(computable_ids)
    results.update(
        {
            qid: (float(ranx_results["map"][i]), float(ranx_results["mrr"][i]))
            for i, qid in enumerate(sorted_computable_ids)
        }
    )
    return results


def _rank_to_score(rank: int) -> float:
    """Rang (1 = meilleur) → score décroissant, pour que le tri interne de
    ``ranx`` reproduise exactement notre ordre de rang, égalités comprises.
    """
    return 1.0 / rank
