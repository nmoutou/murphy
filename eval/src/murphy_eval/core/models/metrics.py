"""La sortie du scorer : métriques par requête, agrégats, ventilation.

ADR-007 : « toujours reporter la distribution par requête, pas seulement la
moyenne ». `MetricsReport.per_query` est donc la donnée primaire ;
`MetricsReport.aggregate` et `by_action_type` sont des commodités dérivées,
jamais un remplacement — le rapport les porte tous les deux, il ne choisit
pas entre eux.

``ndcg_at_r`` est ``float | None`` : une requête sans document pertinent
(R=0) n'a pas de nDCG@R défini (IDCG@R=0, division par zéro). Le modèle le
dit explicitement plutôt que de coder ce cas en 0.0, qui biaiserait
silencieusement la moyenne vers le bas pour une raison étrangère à la
qualité de récupération.
"""

from __future__ import annotations

from pydantic import Field

from murphy_eval.core.models._base import Frozen


class QueryMetrics(Frozen):
    """Les métriques d'une seule requête — niveau document (ADR-006)."""

    query_id: str
    action_type: str | None = None
    r: int = Field(ge=0)
    """Nombre de documents pertinents (grade > 0) pour cette requête."""
    ndcg_at_r: float | None
    """``None`` ssi ``r == 0`` (métrique indéfinie, exclue des moyennes)."""
    map: float
    r_precision: float
    recall_at_2r: float
    doc_mrr: float
    doc_recall_at_r: float


class MetricAggregate(Frozen):
    """Moyenne + effectif d'une métrique, sur les requêtes où elle est définie."""

    ndcg_at_r_mean: float | None
    ndcg_at_r_count: int = Field(ge=0)
    map_mean: float
    r_precision_mean: float
    recall_at_2r_mean: float
    doc_mrr_mean: float
    doc_recall_at_r_mean: float
    query_count: int = Field(ge=0)


class MetricsReport(Frozen):
    """Le rapport complet d'un scoring ``(qrels, run)``."""

    per_query: tuple[QueryMetrics, ...]
    aggregate: MetricAggregate
    by_action_type: tuple[tuple[str, MetricAggregate], ...] = ()
    """Ventilation par type d'action (ADR-009), triée par nom de type."""
