"""Cross-check SECONDAIRE contre ``pytrec_eval`` (ADR-028).

Ce test ne remplace jamais l'oracle primaire (``tests/golden/`` — cas jouets
calculés à la main). Un oracle externe ne fait que **déplacer** le risque ;
il ne le supprime pas. Ce module n'est qu'un second témoin, hors CI par
défaut (marqueur ``oracle``, désélectionné par ``addopts`` du pyproject).

**Constat empirique important, à ne pas re-perdre** : la mesure ``ndcg_cut``
de ``pytrec_eval`` (donc de ``trec_eval``) utilise un **gain LINÉAIRE**
(``rel_i``), pas exponentiel (``2^rel_i - 1``) — vérifié directement contre
cette implémentation (aucun paramètre de gain n'existe sur
``RelevanceEvaluator``). C'est l'inverse de ce qu'on aurait pu supposer par
défaut. Le cross-check compare donc notre ``nDCG@R`` en **mode gain
linéaire** (``linear_gain``, disponible comme mode diagnostic, cf.
``core/models/gains.py``) à ``ndcg_cut`` — jamais notre métrique de
décision par défaut (gain exponentiel), qui n'a pas d'équivalent direct
dans cet outillage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytrec_eval = pytest.importorskip("pytrec_eval")

# Imports du domaine après le skip conditionnel : E402 assumé, cf. pattern
# `pytest.importorskip` standard — ce module ne doit s'importer qu'une fois
# la dépendance oracle confirmée présente.
from murphy_eval.adapters.trec.projection import (  # noqa: E402
    load_trec_qrels,
    load_trec_run,
)
from murphy_eval.core.models.gains import linear_gain  # noqa: E402
from murphy_eval.core.services.aggregation import (  # noqa: E402
    aggregate_qrels,
    aggregate_run,
)
from murphy_eval.core.services.ndcg import ndcg_at_r  # noqa: E402

_DATA_DIR = Path(__file__).parent.parent / "data"

pytestmark = pytest.mark.oracle


def test_ndcg_at_r_gain_lineaire_concorde_avec_pytrec_eval_ndcg_cut() -> None:
    """Le jouet ``toy_a`` a R=3 (trois documents jugés). ``ndcg_cut.3``
    coupe exactement à R=3 pour cette requête : la comparaison est donc
    apples-to-apples (même coupe), ce qui n'est vrai que par construction du
    jouet — un jouet à R variable par requête ne se compare pas ainsi
    (``ndcg_cut`` est une coupe fixe, pas adaptative).
    """
    qrels = load_trec_qrels(_DATA_DIR / "toy_a.qrels")
    run = load_trec_run(
        _DATA_DIR / "toy_a.run", resolve_doc_id=lambda chunk_id: chunk_id
    )

    doc_qrels = aggregate_qrels(qrels)["q1"]
    doc_runs = aggregate_run(run)["q1"]
    ours = ndcg_at_r(doc_qrels.as_dict(), doc_runs.ranked_doc_ids(), gain=linear_gain)

    trec_qrel = {"q1": doc_qrels.as_dict()}
    trec_run = {
        "q1": {
            doc_id: float(len(doc_runs.doc_ranks) - rank + 1)
            for doc_id, rank in doc_runs.doc_ranks
        }
    }
    evaluator = pytrec_eval.RelevanceEvaluator(trec_qrel, {"ndcg_cut.3"})
    theirs = evaluator.evaluate(trec_run)["q1"]["ndcg_cut_3"]

    assert ours == pytest.approx(theirs)
