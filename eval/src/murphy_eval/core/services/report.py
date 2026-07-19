"""L'assembleur : ``(qrels, run) -> MetricsReport`` — le point d'entrée du scorer.

Pipeline, dans l'ordre :

1. agréger qrels et run au niveau document (ADR-006) ;
2. calculer, **par requête**, la métrique de décision (nDCG@R, maison) et les
   diagnostics à coupe adaptative (R-Precision, Recall@2R, Doc-Recall@R,
   maison) ;
3. calculer MAP et Doc-MRR pour toutes les requêtes en un seul appel `ranx` ;
4. assembler la table par requête (ADR-007 : jamais seulement la moyenne),
   l'agrégat global, et la ventilation par type d'action (ADR-009).

``action_types`` est **injecté**, pas connu du scorer : la taxonomie des
requêtes est une propriété du golden-set (B-08), le scorer reste agnostique
de son contenu — il sait seulement grouper par la valeur qu'on lui donne.
"""

from __future__ import annotations

from murphy_eval.core.models.gains import GainFn, exponential_gain
from murphy_eval.core.models.judgment import Qrels
from murphy_eval.core.models.metrics import MetricAggregate, MetricsReport, QueryMetrics
from murphy_eval.core.models.run import Run
from murphy_eval.core.services.aggregation import (
    aggregate_qrels,
    aggregate_run,
    count_relevant,
)
from murphy_eval.core.services.diagnostics import (
    doc_recall_at_r,
    map_and_doc_mrr,
    r_precision,
    recall_at_2r,
)
from murphy_eval.core.services.ndcg import ndcg_at_r


def score(
    qrels: Qrels,
    run: Run,
    *,
    gain: GainFn = exponential_gain,
    action_types: dict[str, str] | None = None,
) -> MetricsReport:
    action_types = action_types or {}

    doc_qrels = aggregate_qrels(qrels)
    doc_runs = aggregate_run(run)
    query_ids = sorted(set(doc_qrels) | set(doc_runs))

    map_mrr_by_query = map_and_doc_mrr(doc_qrels, doc_runs)

    per_query: list[QueryMetrics] = []
    for query_id in query_ids:
        grades = doc_qrels[query_id].as_dict() if query_id in doc_qrels else {}
        ranked = doc_runs[query_id].ranked_doc_ids() if query_id in doc_runs else []
        r = count_relevant(grades)
        map_value, doc_mrr_value = map_mrr_by_query.get(query_id, (0.0, 0.0))

        per_query.append(
            QueryMetrics(
                query_id=query_id,
                action_type=action_types.get(query_id),
                r=r,
                ndcg_at_r=ndcg_at_r(grades, ranked, gain=gain),
                map=map_value,
                r_precision=r_precision(grades, ranked),
                recall_at_2r=recall_at_2r(grades, ranked),
                doc_mrr=doc_mrr_value,
                doc_recall_at_r=doc_recall_at_r(grades, ranked),
            )
        )

    aggregate = _aggregate(per_query)
    by_action_type = _by_action_type(per_query)

    return MetricsReport(
        per_query=tuple(per_query),
        aggregate=aggregate,
        by_action_type=by_action_type,
    )


def _aggregate(per_query: list[QueryMetrics]) -> MetricAggregate:
    ndcg_values = [q.ndcg_at_r for q in per_query if q.ndcg_at_r is not None]
    count = len(per_query)
    return MetricAggregate(
        ndcg_at_r_mean=_mean(ndcg_values) if ndcg_values else None,
        ndcg_at_r_count=len(ndcg_values),
        map_mean=_mean([q.map for q in per_query]),
        r_precision_mean=_mean([q.r_precision for q in per_query]),
        recall_at_2r_mean=_mean([q.recall_at_2r for q in per_query]),
        doc_mrr_mean=_mean([q.doc_mrr for q in per_query]),
        doc_recall_at_r_mean=_mean([q.doc_recall_at_r for q in per_query]),
        query_count=count,
    )


def _by_action_type(
    per_query: list[QueryMetrics],
) -> tuple[tuple[str, MetricAggregate], ...]:
    grouped: dict[str, list[QueryMetrics]] = {}
    for query_metrics in per_query:
        if query_metrics.action_type is None:
            continue
        grouped.setdefault(query_metrics.action_type, []).append(query_metrics)
    return tuple(
        (action_type, _aggregate(queries))
        for action_type, queries in sorted(grouped.items())
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
