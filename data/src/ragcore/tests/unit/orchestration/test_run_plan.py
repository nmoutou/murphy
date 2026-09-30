"""Le plan du run : dérivé une fois, en tête de run, sans rien ouvrir."""

import copy
import logging
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from ragcore.adapters.config.settings import Environment, InfraSettings
from ragcore.adapters.storage.neo4j.node_properties import NodeHydration
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.orchestration.kedro.run_parameters import SAFE_DEV_SETTINGS
from ragcore.orchestration.kedro.run_plan import plan_run

PARAMS: dict[str, Any] = {
    "chunking": {"max_chars": 384, "overlap_chars": 25},
    "dev": {
        "nuke_all": False,
        "embedding_enabled": True,
        "skip_unconfigured": False,
        "node_hydration": {"include_path": True, "include_content": True},
    },
}
"""Les clés de `parameters.yml` sans défaut dans le code."""

BOOLEAN_PATHS = [
    "dev.nuke_all",
    "dev.embedding_enabled",
    "dev.skip_unconfigured",
    "dev.node_hydration.include_path",
    "dev.node_hydration.include_content",
]
"""Les booléens du YAML : stricts, obligatoires, validés dans tous les environnements."""

RISKIEST_DEV: dict[str, Any] = {
    "nuke_all": True,
    "embedding_enabled": False,
    "skip_unconfigured": False,
    "node_hydration": {"include_path": True, "include_content": True},
}
"""Le bloc `dev` réglé au plus risqué pour une prod."""

SHIPPED_PARAMETERS = Path(__file__).parents[5] / "conf/base/parameters.yml"
"""Le `parameters.yml` livré, celui que lit `kedro run`."""


def _settings(environment: Environment = "prod") -> InfraSettings:
    return InfraSettings(
        source="all", environment=environment, qdrant_collection="chunks"
    )


def _path(path: str) -> str:
    """Le motif d'un chemin pointé tel que le message d'erreur le cite."""
    return re.escape(f"`{path}`")


def _with(path: str, value: object) -> dict[str, Any]:
    """Une copie de `PARAMS` où la clé au chemin pointé `path` vaut `value`."""
    params = copy.deepcopy(PARAMS)
    *parents, key = path.split(".")
    block = params
    for parent in parents:
        block = block[parent]
    block[key] = value
    return params


def _without(path: str) -> dict[str, Any]:
    """Une copie de `PARAMS` sans la clé au chemin pointé `path`."""
    params = copy.deepcopy(PARAMS)
    *parents, key = path.split(".")
    block = params
    for parent in parents:
        block = block[parent]
    del block[key]
    return params


def test_un_run_nu_ecrit_la_collection_configuree() -> None:
    plan = plan_run(PARAMS, _settings())

    assert plan.context_source is None, "un run multi-source n'a pas de source"
    assert plan.collection == "chunks"
    assert (plan.chunking.max_chars, plan.chunking.overlap_chars) == (384, 25)


def test_sans_reglage_de_decoupe_le_run_s_arrete() -> None:
    with pytest.raises(ValueError, match=_path("chunking")):
        plan_run(_without("chunking"), _settings())


def test_un_reglage_de_traitement_mal_forme_arrete_le_run() -> None:
    params = _with("chunking", {"max_chars": 0, "overlap_chars": 25})

    with pytest.raises(ValueError, match="max_chars"):
        plan_run(params, _settings())


@pytest.mark.parametrize("overlap_chars", [384, 400])
def test_un_recouvrement_qui_n_est_pas_inferieur_a_la_taille_arrete_le_run(
    overlap_chars: int,
) -> None:
    """Le curseur de la fenêtre glissante n'avancerait pas : boucle infinie."""
    params = _with("chunking.overlap_chars", overlap_chars)

    with pytest.raises(ValueError, match=_path("chunking")):
        plan_run(params, _settings())


def test_un_run_restreint_garde_sa_source() -> None:
    plan = plan_run(_with("source", "cass"), _settings())

    assert plan.sources == (SourceName.CASS,)
    assert plan.context_source is SourceName.CASS


def test_une_source_inconnue_echoue_avant_d_ouvrir_quoi_que_ce_soit() -> None:
    with pytest.raises(ValueError, match="Source inconnue"):
        plan_run(_with("source", "cas"), _settings())


@pytest.mark.parametrize("path", BOOLEAN_PATHS)
def test_sans_booleen_le_run_s_arrete_meme_hors_dev(path: str) -> None:
    with pytest.raises(ValueError, match=_path(path)):
        plan_run(_without(path), _settings("prod"))


@pytest.mark.parametrize("value", [None, "false", 0])
@pytest.mark.parametrize("path", BOOLEAN_PATHS)
def test_un_booleen_mal_type_arrete_le_run_meme_hors_dev(
    path: str, value: object
) -> None:
    """``"false"`` est une chaîne non vide : lue avec ``bool(...)``, elle vaudrait vrai."""
    with pytest.raises(ValueError, match=_path(path)):
        plan_run(_with(path, value), _settings("prod"))


def test_en_dev_le_bloc_dev_s_applique_tel_quel() -> None:
    plan = plan_run(_with("dev", RISKIEST_DEV), _settings("dev"))

    assert plan.nuke_all is True
    assert plan.embedding_enabled is False
    assert plan.skip_unconfigured is False
    assert plan.node_hydration == NodeHydration(
        metadata=True, include_path=True, include_content=True
    )


def test_l_hydratation_neo4j_vient_du_yaml_en_dev() -> None:
    params = _with("dev.node_hydration.include_path", False)

    hydration = plan_run(params, _settings("dev")).node_hydration

    assert (hydration.include_path, hydration.include_content) == (False, True)


def test_hors_dev_le_bloc_dev_est_ignore() -> None:
    """Même réglé au plus risqué, le bloc `dev` ne touche pas une prod."""
    plan = plan_run(_with("dev", RISKIEST_DEV), _settings("prod"))

    assert plan.nuke_all is SAFE_DEV_SETTINGS.nuke_all is False
    assert plan.embedding_enabled is True
    assert plan.skip_unconfigured is True
    assert plan.node_hydration == NodeHydration()


def test_hors_dev_un_avertissement_signale_le_bloc_ignore(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        plan_run(PARAMS, _settings("prod"))

    assert "le bloc `dev` de parameters.yml est ignoré" in caplog.text


def test_en_dev_aucun_avertissement_de_bloc_ignore(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        plan_run(PARAMS, _settings("dev"))

    assert "est ignoré" not in caplog.text


def test_les_labels_neo4j_viennent_des_sources() -> None:
    labels = plan_run(PARAMS, _settings()).node_labels

    assert labels.label_for(Identifier(raw="LEGIARTI000006419264")) == "Article"
    assert labels.label_for(Identifier(raw="JURITEXT000019333891")) == "Document"
    assert labels.known == ("Document", "Article", "Texte", "Section")


@pytest.mark.parametrize(
    "path", ["nlp", "dev.node_hydration.include_pth", "chunking.max_char"]
)
def test_une_cle_inconnue_arrete_le_run(path: str) -> None:
    """Une clé morte ou mal orthographiée ne passe plus en silence, à aucun niveau."""
    with pytest.raises(ValueError, match=_path(path)):
        plan_run(_with(path, True), _settings())


@pytest.mark.parametrize(
    "block",
    ["maintenance", "exportation", "embedding_runtime", "embedding", "node_labels"],
)
def test_l_ancienne_forme_est_refusee(block: str) -> None:
    """Un `parameters.yml` resté à une ancienne forme arrête le run. Le bloc `embedding`
    est parti dans l'environnement : `EMBEDDING_MODEL`, et une dimension mesurée ; le
    bloc `node_labels` dans le registre des sources."""
    with pytest.raises(ValueError, match=_path(block)):
        plan_run(_with(block, {}), _settings())


def test_un_params_mal_orthographie_arrete_le_run() -> None:
    """Kedro fusionne les `--params` dans les paramètres : `sorce=cass` est une clé
    inconnue, pas un run sur toutes les sources."""
    with pytest.raises(ValueError, match=_path("sorce")):
        plan_run(_with("sorce", "cass"), _settings())


def test_un_entier_ecrit_en_chaine_arrete_le_run() -> None:
    with pytest.raises(ValueError, match=_path("chunking.max_chars")):
        plan_run(_with("chunking.max_chars", "384"), _settings())


def test_toutes_les_erreurs_sont_signalees_ensemble() -> None:
    params = _with("dev.nuke_all", "false")
    del params["chunking"]

    with pytest.raises(ValueError) as raised:
        plan_run(params, _settings())

    assert "`dev.nuke_all`" in str(raised.value)
    assert "`chunking`" in str(raised.value)


def test_le_parameters_yml_livre_est_valide() -> None:
    params = yaml.safe_load(SHIPPED_PARAMETERS.read_text(encoding="utf-8"))

    assert plan_run(params, _settings("dev")).collection == "chunks"
