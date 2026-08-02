"""CLIQUET — le scorer, contre des cas jouets calculés à la main (ADR-028).

⚠️ **La métrique testée ici est dépréciée** : ``nDCG@R`` est retiré le 2 août 2026
(ticket #14, ADR-007 réécrit autour de ``RBP(p) + résidu``). Ces cliquets restent
verts et sont **conservés comme patron** pour les cliquets de B-15 — c'est la
*méthode* (oracle auto pur, valeurs calculées à la main) qui est reprise, pas la
métrique. Voir ``core/services/ndcg.py`` pour le détail.

Le régime de vérification du scorer est **auto pur** : ADR-006 l'a voulu
« trivial et neutre » précisément pour qu'aucun jugement n'y vive, et
ADR-028 exige que son test se fasse « contre des cas jouets vérifiables à la
main par un tiers, sans oracle externe qui ne ferait que déplacer le
risque ». Ce module EST cet oracle — pas ``tests/oracle/`` (qui n'est qu'un
second témoin, ``trec_eval``, jamais l'arbitre).

Chaque cas porte l'arithmétique en commentaire. Un tiers qui ne fait pas
confiance à ce fichier doit pouvoir reposer les calculs sur papier et
retomber sur les mêmes littéraux — c'est le contrat.

Un test unitaire échoue quand on casse le code. Un golden échoue aussi quand
on change une convention sans s'en rendre compte (la fonction de gain, la
règle de coupe R, la règle d'agrégation ADR-006) : les littéraux ci-dessous
rendent ce changement visible en revue, comme ``golden/test_fingerprint.py``
côté ``ragcore`` le fait pour l'empreinte de config.
"""

from __future__ import annotations

from murphy_eval.core.models.aggregated import DocQrels, DocRun
from murphy_eval.core.models.gains import exponential_gain, linear_gain
from murphy_eval.core.models.judgment import Judgment, Qrels
from murphy_eval.core.models.run import Run, RunEntry
from murphy_eval.core.services.aggregation import aggregate_qrels, aggregate_run
from murphy_eval.core.services.diagnostics import (
    doc_recall_at_r,
    map_and_doc_mrr,
    r_precision,
    recall_at_2r,
)
from murphy_eval.core.services.ndcg import ndcg_at_r
from murphy_eval.core.services.report import score

# Poids positionnel du DCG, i 0-based : 1/log2(i+2).
# pos1 = 1/log2(2) = 1.0
# pos2 = 1/log2(3) ≈ 0.6309297535714575
# pos3 = 1/log2(4) = 0.5
#
# Gain exponentiel (2^rel - 1) : grade 0/1/2/3 -> gain 0/1/3/7.


def _doc_qrels(query_id: str, grades: dict[str, int]) -> DocQrels:
    return DocQrels(query_id=query_id, doc_grades=tuple(sorted(grades.items())))


def _doc_run(query_id: str, ranked_doc_ids: list[str]) -> DocRun:
    return DocRun(
        query_id=query_id,
        doc_ranks=tuple(
            (doc_id, rank) for rank, doc_id in enumerate(ranked_doc_ids, 1)
        ),
    )


class TestCasA_ChunkNiveauSansAgregation:
    """qrels {d1=3, d2=2, d3=1} ; run [d2, d1, d4, d3] (d4 non pertinent).

    R = 3 (trois documents de grade > 0). Top-R = [d2, d1, d4].

    Gain exponentiel : run_gains [3, 7, 0].
        DCG@R  = 3·1.0 + 7·0.6309297535714575 + 0·0.5 = 7.4165082750002025
    Gains idéaux triés desc [7, 3, 1] :
        IDCG@R = 7·1.0 + 3·0.6309297535714575 + 1·0.5 = 9.392789260714373
        nDCG@R = 7.4165082750002025 / 9.392789260714373 = 0.7895959410076381
    """

    _GRADES = {"d1": 3, "d2": 2, "d3": 1}
    _RANKED = ["d2", "d1", "d4", "d3"]

    def test_ndcg_at_r_gain_exponentiel(self) -> None:
        assert ndcg_at_r(self._GRADES, self._RANKED, gain=exponential_gain) == (
            0.7895959410076381
        )

    def test_ndcg_at_r_gain_lineaire(self) -> None:
        """Même cas, gain linéaire (rel) : prouve que le gain est injectable.

        run_gains [2, 3, 0] : DCG@R = 2·1.0 + 3·0.6309297535714575 + 0·0.5
                                     = 3.8927892607143724
        Idéal desc [3, 2, 1] : IDCG@R = 3 + 2·0.6309297535714575 + 0.5
                                       = 4.7618595071429155
        nDCG@R = 3.8927892607143724 / 4.7618595071429155 = 0.8174935137996165
        """
        assert ndcg_at_r(self._GRADES, self._RANKED, gain=linear_gain) == (
            0.8174935137996165
        )

    def test_r_precision(self) -> None:
        """2 documents pertinents dans le top-3 (d2, d1 ; pas d4) -> 2/3."""
        assert r_precision(self._GRADES, self._RANKED) == 0.6666666666666666

    def test_recall_at_2r(self) -> None:
        """Top-6 (liste de 4) contient les 3 pertinents -> 1.0."""
        assert recall_at_2r(self._GRADES, self._RANKED) == 1.0

    def test_map_via_ranx(self) -> None:
        """AP : hits en positions 1 (d2), 2 (d1), 4 (d3) -> precision (1, 1, 0.75)
        moyennées sur les 3 pertinents = (1 + 1 + 0.75)/3 = 0.9166666666666666.
        """
        doc_qrels = {"q1": _doc_qrels("q1", self._GRADES)}
        doc_runs = {"q1": _doc_run("q1", self._RANKED)}
        map_value, _mrr = map_and_doc_mrr(doc_qrels, doc_runs)["q1"]
        assert map_value == 0.9166666666666666


class TestCasB_RankingParfait:
    """qrels {a=3, b=2} ; run [a, b, c]. R=2, top-R=[a,b] = les 2 pertinents
    dans l'ordre idéal -> nDCG@R = 1.0 exactement.
    """

    _GRADES = {"a": 3, "b": 2}
    _RANKED = ["a", "b", "c"]

    def test_ndcg_at_r_parfait(self) -> None:
        assert ndcg_at_r(self._GRADES, self._RANKED) == 1.0

    def test_doc_mrr_parfait(self) -> None:
        doc_qrels = {"q1": _doc_qrels("q1", self._GRADES)}
        doc_runs = {"q1": _doc_run("q1", self._RANKED)}
        _map, mrr = map_and_doc_mrr(doc_qrels, doc_runs)["q1"]
        assert mrr == 1.0


class TestCasC_AgregationChunkVersDocument:
    """Chunks : D1={c1=3, c2=1}, D2={c3=2}, D3={c4=0}.
    Run (ordre de rang croissant, niveau chunk) : [c3, c2, c4, c1].

    Agrégation qrels (max, ADR-006) : D1=3, D2=2, D3=0.
    Agrégation run (rang du 1er chunk, ADR-006) :
        D2 vu en 1er (c3, rang1), D1 en 2e (c2, rang2), D3 en 3e (c4, rang3) ;
        c1 (D1, rang4) ignoré : D1 a déjà un rang.
        -> doc run = [D2, D1, D3].

    R = 2 (D1, D2 ; D3 est grade 0, non pertinent). Top-R = [D2, D1].
    Gains exp : [3, 7]. DCG@R = 3·1.0 + 7·0.6309297535714575 = 7.4165082750002025
    Idéal desc [7, 3] : IDCG@R = 7 + 3·0.6309297535714575 = 8.892789260714373
    nDCG@R = 7.4165082750002025 / 8.892789260714373 = 0.8339912323981488

    Ce cas est la preuve, à lui seul, que l'agrégation (max qrels, 1er-chunk
    + dédup runs) est appliquée AVANT le calcul du nDCG@R.
    """

    def _qrels_chunk_niveau(self) -> Qrels:
        return Qrels(
            judgments=(
                Judgment(query_id="q1", doc_id="D1", chunk_id="c1", grade=3),
                Judgment(query_id="q1", doc_id="D1", chunk_id="c2", grade=1),
                Judgment(query_id="q1", doc_id="D2", chunk_id="c3", grade=2),
                Judgment(query_id="q1", doc_id="D3", chunk_id="c4", grade=0),
            )
        )

    def _run_chunk_niveau(self) -> Run:
        # Ordre de rang croissant (le plus proche de la tête = rang le plus bas).
        return Run(
            entries=(
                RunEntry(query_id="q1", chunk_id="c3", doc_id="D2", rank=1, score=4.0),
                RunEntry(query_id="q1", chunk_id="c2", doc_id="D1", rank=2, score=3.0),
                RunEntry(query_id="q1", chunk_id="c4", doc_id="D3", rank=3, score=2.0),
                RunEntry(query_id="q1", chunk_id="c1", doc_id="D1", rank=4, score=1.0),
            )
        )

    def test_agregation_qrels_prend_le_max(self) -> None:
        doc_qrels = aggregate_qrels(self._qrels_chunk_niveau())
        assert doc_qrels["q1"].as_dict() == {"D1": 3, "D2": 2, "D3": 0}

    def test_agregation_run_prend_le_rang_du_premier_chunk(self) -> None:
        doc_runs = aggregate_run(self._run_chunk_niveau())
        assert doc_runs["q1"].ranked_doc_ids() == ["D2", "D1", "D3"]

    def test_ndcg_at_r_apres_agregation(self) -> None:
        doc_qrels = aggregate_qrels(self._qrels_chunk_niveau())["q1"]
        doc_runs = aggregate_run(self._run_chunk_niveau())["q1"]
        result = ndcg_at_r(doc_qrels.as_dict(), doc_runs.ranked_doc_ids())
        assert result == 0.8339912323981488

    def test_doc_recall_at_r_apres_agregation(self) -> None:
        doc_qrels = aggregate_qrels(self._qrels_chunk_niveau())["q1"]
        doc_runs = aggregate_run(self._run_chunk_niveau())["q1"]
        # top-R=[D2, D1], les deux pertinents -> 1.0.
        assert doc_recall_at_r(doc_qrels.as_dict(), doc_runs.ranked_doc_ids()) == 1.0

    def test_report_bout_en_bout_niveau_chunk(self) -> None:
        """Le pipeline complet (``score``) prend des qrels/run niveau CHUNK en
        entrée et retombe sur le même littéral que le calcul manuel ci-dessus
        — preuve que ``report.score`` agrège avant de scorer, jamais après.
        """
        report = score(self._qrels_chunk_niveau(), self._run_chunk_niveau())
        assert len(report.per_query) == 1
        assert report.per_query[0].ndcg_at_r == 0.8339912323981488


class TestCasD_AucunDocumentPertinent:
    """R=0 : nDCG@R est indéfini (IDCG nul), jamais 0.0 — la moyenne ne doit
    pas être biaisée par une requête où la métrique n'a pas de sens.
    """

    def test_ndcg_at_r_est_none(self) -> None:
        assert ndcg_at_r({"a": 0, "b": 0}, ["a", "b"]) is None

    def test_requete_r0_conservee_dans_per_query_mais_exclue_de_la_moyenne(
        self,
    ) -> None:
        qrels = Qrels(
            judgments=(Judgment(query_id="q1", doc_id="a", chunk_id="a#0", grade=0),)
        )
        run = Run(
            entries=(
                RunEntry(query_id="q1", chunk_id="a#0", doc_id="a", rank=1, score=1.0),
            )
        )
        report = score(qrels, run)
        assert len(report.per_query) == 1
        assert report.per_query[0].ndcg_at_r is None
        assert report.aggregate.ndcg_at_r_mean is None
        assert report.aggregate.ndcg_at_r_count == 0


class TestCasE_RunVideAvecPertinents:
    """R>0 mais aucun document récupéré : nDCG@R = 0.0 (aucun gain), pas de
    crash — cas valide et distinct du R=0 (Cas D).
    """

    def test_ndcg_at_r_run_vide(self) -> None:
        assert ndcg_at_r({"x": 2, "y": 1}, []) == 0.0


class TestCasF_DepartageDeterministe:
    """Deux chunks au même rang d'entrée : le départage (ordre d'entrée, puis
    ``chunk_id`` croissant) doit produire un ordre stable et reproductible.
    """

    def test_egalite_de_rang_departagee_par_chunk_id(self) -> None:
        run = Run(
            entries=(
                RunEntry(query_id="q1", chunk_id="cZ", doc_id="DZ", rank=1, score=5.0),
                RunEntry(query_id="q1", chunk_id="cA", doc_id="DA", rank=1, score=5.0),
            )
        )
        doc_runs = aggregate_run(run)
        # À rang égal, chunk_id croissant décide : cA avant cZ.
        assert doc_runs["q1"].ranked_doc_ids() == ["DA", "DZ"]

    def test_determinisme_meme_entree_deux_appels(self) -> None:
        run = Run(
            entries=(
                RunEntry(query_id="q1", chunk_id="c3", doc_id="D2", rank=1, score=4.0),
                RunEntry(query_id="q1", chunk_id="c2", doc_id="D1", rank=2, score=3.0),
            )
        )
        assert aggregate_run(run) == aggregate_run(run)
