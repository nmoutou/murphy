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
from ragcore.core.models.processing import ChunkingConfig
from ragcore.orchestration.kedro.run_parameters import SAFE_DEV_SETTINGS
from ragcore.orchestration.kedro.run_plan import plan_run

CHUNKING = ChunkingConfig(max_chars=384, overlap_chars=25)
"""La découpe, lue de l'environnement par ``ChunkingSettings``, hors de ces tests."""

PARAMS: dict[str, Any] = {
    "nuke_all": False,
    "embedding_enabled": True,
    "skip_unconfigured": False,
    "include_path": True,
    "include_content_neo4j": True,
}
"""Les clés de `parameters.yml` sans défaut dans le code."""

BOOLEAN_PATHS = [
    "nuke_all",
    "embedding_enabled",
    "skip_unconfigured",
    "include_path",
    "include_content_neo4j",
]
"""Les booléens du YAML : stricts, obligatoires, validés dans tous les environnements."""

RISKIEST_DEV: dict[str, Any] = {
    "nuke_all": True,
    "embedding_enabled": False,
    "skip_unconfigured": False,
    "include_path": True,
    "include_content_neo4j": True,
}
"""`parameters.yml` réglé au plus risqué pour une prod."""

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
    plan = plan_run(PARAMS, _settings(), CHUNKING)

    assert len(plan.sources) > 1, "un run nu ingère toutes les sources"
    assert plan.collection == "chunks"
    assert plan.chunking == CHUNKING


def test_un_run_restreint_garde_sa_source() -> None:
    plan = plan_run(_with("source", "cass"), _settings(), CHUNKING)

    assert plan.sources == (SourceName.CASS,)


def test_une_source_inconnue_echoue_avant_d_ouvrir_quoi_que_ce_soit() -> None:
    with pytest.raises(ValueError, match="Source inconnue"):
        plan_run(_with("source", "cas"), _settings(), CHUNKING)


@pytest.mark.parametrize("path", BOOLEAN_PATHS)
def test_sans_booleen_le_run_s_arrete_meme_hors_dev(path: str) -> None:
    with pytest.raises(ValueError, match=_path(path)):
        plan_run(_without(path), _settings("prod"), CHUNKING)


@pytest.mark.parametrize("value", [None, "false", 0])
@pytest.mark.parametrize("path", BOOLEAN_PATHS)
def test_un_booleen_mal_type_arrete_le_run_meme_hors_dev(
    path: str, value: object
) -> None:
    """``"false"`` est une chaîne non vide : lue avec ``bool(...)``, elle vaudrait vrai."""
    with pytest.raises(ValueError, match=_path(path)):
        plan_run(_with(path, value), _settings("prod"), CHUNKING)


def test_en_dev_le_fichier_s_applique_tel_quel() -> None:
    plan = plan_run(RISKIEST_DEV, _settings("dev"), CHUNKING)

    assert plan.nuke_all is True
    assert plan.embedding_enabled is False
    assert plan.skip_unconfigured is False
    assert plan.include_path is True
    assert plan.node_hydration == NodeHydration(
        metadata=True, include_path=True, include_content=True
    )


def test_l_hydratation_neo4j_vient_du_yaml_en_dev() -> None:
    params = _with("include_path", False)

    plan = plan_run(params, _settings("dev"), CHUNKING)

    assert plan.include_path is False
    hydration = plan.node_hydration
    assert (hydration.include_path, hydration.include_content) == (False, True)


def test_hors_dev_le_fichier_est_ignore() -> None:
    """Même réglé au plus risqué, `parameters.yml` ne touche pas une prod."""
    plan = plan_run(RISKIEST_DEV, _settings("prod"), CHUNKING)

    assert plan.nuke_all is SAFE_DEV_SETTINGS.nuke_all is False
    assert plan.embedding_enabled is True
    assert plan.skip_unconfigured is True
    assert plan.include_path is False
    assert plan.node_hydration == NodeHydration()


def test_hors_dev_un_avertissement_signale_le_fichier_ignore(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        plan_run(PARAMS, _settings("prod"), CHUNKING)

    assert "parameters.yml est ignoré" in caplog.text


def test_en_dev_aucun_avertissement_de_fichier_ignore(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        plan_run(PARAMS, _settings("dev"), CHUNKING)

    assert "est ignoré" not in caplog.text


def test_les_labels_neo4j_viennent_des_sources() -> None:
    labels = plan_run(PARAMS, _settings(), CHUNKING).node_labels

    assert labels.label_for(Identifier(raw="LEGIARTI000006419264")) == "Article"
    assert labels.label_for(Identifier(raw="JURITEXT000019333891")) == "Document"


@pytest.mark.parametrize("path", ["nlp", "include_pth", "nuke_al"])
def test_une_cle_inconnue_arrete_le_run(path: str) -> None:
    """Une clé morte ou mal orthographiée ne passe plus en silence, à aucun niveau."""
    with pytest.raises(ValueError, match=_path(path)):
        plan_run(_with(path, True), _settings(), CHUNKING)


@pytest.mark.parametrize(
    "block",
    [
        "maintenance",
        "exportation",
        "embedding_runtime",
        "embedding",
        "node_labels",
        "chunking",
        "dev",
        "node_hydration",
    ],
)
def test_l_ancienne_forme_est_refusee(block: str) -> None:
    """Un `parameters.yml` resté à une ancienne forme arrête le run. Le bloc `embedding`
    est parti dans l'environnement : `EMBEDDING_MODEL`, et une dimension mesurée ; le
    bloc `chunking` aussi, à côté du modèle (`CHUNKING_*`) ; le bloc `node_labels` dans
    le registre des sources. Le bloc `dev` est devenu le fichier entier, et
    `node_hydration` s'est aplati en `include_path` et `include_content_neo4j`."""
    with pytest.raises(ValueError, match=_path(block)):
        plan_run(_with(block, {}), _settings(), CHUNKING)


def test_une_source_mal_typee_est_signalee_a_son_chemin() -> None:
    """``source`` est rangée à part, mais son erreur est listée avec celles du fichier."""
    params = _with("source", 3)
    del params["nuke_all"]

    with pytest.raises(ValueError) as raised:
        plan_run(params, _settings(), CHUNKING)

    assert "`source`" in str(raised.value)
    assert "`nuke_all`" in str(raised.value)


def test_hors_dev_la_source_s_applique() -> None:
    """``source`` n'est pas une commodité de dev : la prod la respecte."""
    plan = plan_run(_with("source", "cass"), _settings("prod"), CHUNKING)

    assert plan.sources == (SourceName.CASS,)


def test_un_params_mal_orthographie_arrete_le_run() -> None:
    """Kedro fusionne les `--params` dans les paramètres : `sorce=cass` est une clé
    inconnue, pas un run sur toutes les sources."""
    with pytest.raises(ValueError, match=_path("sorce")):
        plan_run(_with("sorce", "cass"), _settings(), CHUNKING)


def test_toutes_les_erreurs_sont_signalees_ensemble() -> None:
    params = _with("nuke_all", "false")
    del params["skip_unconfigured"]

    with pytest.raises(ValueError) as raised:
        plan_run(params, _settings(), CHUNKING)

    assert "`nuke_all`" in str(raised.value)
    assert "`skip_unconfigured`" in str(raised.value)


def test_le_parameters_yml_livre_est_valide() -> None:
    params = yaml.safe_load(SHIPPED_PARAMETERS.read_text(encoding="utf-8"))

    assert plan_run(params, _settings("dev"), CHUNKING).collection == "chunks"
