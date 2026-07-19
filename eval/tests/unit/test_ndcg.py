from __future__ import annotations

from murphy_eval.core.models.gains import exponential_gain, linear_gain
from murphy_eval.core.services.ndcg import dcg, ndcg_at_r


def test_dcg_gain_unique_position_1() -> None:
    assert dcg([5.0]) == 5.0


def test_dcg_ponderation_positionnelle_decroissante() -> None:
    """Le même gain vaut moins loin dans le classement."""
    assert dcg([1.0, 0.0]) > dcg([0.0, 1.0])


def test_dcg_liste_vide() -> None:
    assert dcg([]) == 0.0


def test_ndcg_at_r_ignore_les_documents_hors_du_top_r() -> None:
    """Un document non pertinent au-delà de la coupe R ne doit strictement
    rien changer au score.
    """
    grades = {"a": 3}
    sans_bruit = ndcg_at_r(grades, ["a"])
    avec_bruit = ndcg_at_r(grades, ["a", "non_pertinent_1", "non_pertinent_2"])
    assert sans_bruit == avec_bruit


def test_ndcg_at_r_r_zero_retourne_none() -> None:
    assert ndcg_at_r({}, []) is None
    assert ndcg_at_r({"a": 0}, ["a"]) is None


def test_ndcg_at_r_run_vide_retourne_zero() -> None:
    assert ndcg_at_r({"a": 1}, []) == 0.0


def test_ndcg_at_r_gain_par_defaut_est_exponentiel() -> None:
    grades = {"a": 3, "b": 1}
    ranked = ["b", "a"]
    assert ndcg_at_r(grades, ranked) == ndcg_at_r(grades, ranked, gain=exponential_gain)


def test_ndcg_at_r_injection_de_gain_change_le_resultat() -> None:
    """Preuve que le gain est bien injecté : deux fonctions différentes sur
    un classement non idéal donnent des résultats différents.
    """
    grades = {"a": 3, "b": 1}
    ranked = ["b", "a"]  # non idéal : le grade 1 avant le grade 3
    exp_result = ndcg_at_r(grades, ranked, gain=exponential_gain)
    lin_result = ndcg_at_r(grades, ranked, gain=linear_gain)
    assert exp_result != lin_result


def test_ndcg_at_r_borne_a_1_malgre_un_doublon_dans_le_run() -> None:
    """Un ``doc_id`` en double dans ``ranked_doc_ids`` ne doit jamais faire
    dépasser 1.0 : le doublon est le même document reclassé, pas un second
    gain. ``aggregate_run`` déduplique déjà en amont ; cette fonction pure se
    défend seule pour l'appelant qui la sollicite hors de ce chemin (B-05).
    """
    grades = {"a": 3, "b": 1}
    # Le doublon est ignoré : ["a", "a"] est traité comme ["a"] (un seul
    # document récupéré, le second pertinent jamais atteint), et non comme
    # deux gains cumulés — ce qui, sans garde-fou, donnait 1.496.
    assert ndcg_at_r(grades, ["a", "a"]) == ndcg_at_r(grades, ["a"])
    assert ndcg_at_r(grades, ["a", "a"]) <= 1.0


def test_ndcg_at_r_document_non_juge_vaut_gain_zero() -> None:
    """Un document présent dans le run mais absent des qrels (jamais jugé)
    contribue un gain de 0, comme un document jugé non pertinent.
    """
    grades = {"a": 3}
    avec_inconnu = ndcg_at_r(grades, ["inconnu", "a"])
    equivalent = ndcg_at_r({"a": 3, "inconnu": 0}, ["inconnu", "a"])
    assert avec_inconnu == equivalent
