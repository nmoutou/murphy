"""⚠️ DÉPRÉCIÉ — nDCG@R n'est plus la métrique de décision (2 août 2026).

ADR-007 a été **réécrit** (ticket #14, https://github.com/left-eyebr0w/murphy/issues/14) :
``nDCG@R`` est **retiré**, remplacé par ``RBP(p) + résidu``. Motif décisif, et il
est interne : ``nDCG@R`` ne s'appliquait qu'à la branche des ensembles *ouverts*,
qui est peuplée des seuls 30 cas jugés — le seul endroit du dispositif où ``R``
n'est ni connu ni estimable. Moffat & Zobel (TOIS 2008, §4.6) disqualifient par
ailleurs nommément nDCG dans ce régime.

**Ce module est conservé, non supprimé**, jusqu'à ce que le scorer ``RBP``
existe (backlog B-15) : son harnais d'oracle *auto pur*, sa discipline de gain
injectable et le cross-check ``pytrec_eval`` sont le patron sur lequel B-15
s'écrira. **Ne pas l'appeler pour trancher une comparaison de configurations.**

Note pour B-15 : la convention de gain figée par ADR-007 est désormais la
**projection linéaire** ``g/3`` (ADR-005) — l'échelle 0-3 est un *compte de
portes franchies*, non une intensité. Le défaut exponentiel ci-dessous est
l'ancienne convention de nDCG et **ne se transporte pas** vers RBP.

---

Rédaction antérieure :

nDCG@R — la métrique de décision (ADR-007), MAISON, sans coupe fixe.

`ranx` ne connaît que des coupes fixes ``@k`` : c'est précisément le point
que rejette ADR-007 (« les k fixes relèvent du modèle web search, incompatible
avec l'invariant d'exhaustivité des sources »). La coupe adaptative — R =
nombre de documents pertinents *de cette requête* — est donc calculée ici,
sans jamais solliciter `ranx` pour le nDCG.

Convention de gain : voir ``core/models/gains.py``. Le défaut (exponentiel)
est la convention **figée** de la métrique de décision ; le linéaire est un
mode diagnostic, jamais celui qui tranche une comparaison de configs.
"""

from __future__ import annotations

from math import log2

from murphy_eval.core.models.gains import GainFn, exponential_gain
from murphy_eval.core.services.aggregation import dedup_first


def dcg(gains: list[float]) -> float:
    """Discounted Cumulative Gain : poids positionnel ``1/log2(i+2)``, i 0-based."""
    return sum(gain / log2(index + 2) for index, gain in enumerate(gains))


def ndcg_at_r(
    doc_grades: dict[str, int],
    ranked_doc_ids: list[str],
    *,
    gain: GainFn = exponential_gain,
) -> float | None:
    """nDCG à la coupe adaptative R = nombre de documents pertinents.

    - ``doc_grades`` : grades niveau document pour la requête (sortie de
      ``aggregate_qrels``), ``doc_id -> grade`` (0..3).
    - ``ranked_doc_ids`` : documents dans l'ordre de rang croissant (sortie de
      ``aggregate_run``, ``DocRun.ranked_doc_ids()``).

    Retourne ``None`` si R=0 (aucun document pertinent pour cette requête) :
    l'IDCG serait nul, la métrique est indéfinie plutôt que valant 0 — la
    différence compte pour ne pas biaiser une moyenne avec des requêtes où la
    question n'a mathématiquement pas de sens. Un ``ranked_doc_ids`` vide
    (run vide) avec R>0 est un cas valide et distinct : il donne 0.0 (aucun
    gain récupéré), pas ``None``.
    """
    relevant_grades = [g for g in doc_grades.values() if g > 0]
    r = len(relevant_grades)
    if r == 0:
        return None

    top_r = dedup_first(ranked_doc_ids)[:r]
    run_gains = [gain(doc_grades.get(doc_id, 0)) for doc_id in top_r]
    ideal_gains = sorted((gain(g) for g in relevant_grades), reverse=True)[:r]

    idcg = dcg(ideal_gains)
    return dcg(run_gains) / idcg
