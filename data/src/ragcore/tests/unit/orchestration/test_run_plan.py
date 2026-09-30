"""Le plan du run : dérivé une fois, en tête de run, sans rien ouvrir."""

import copy
from typing import Any

import pytest

from ragcore.adapters.config.settings import InfraSettings
from ragcore.adapters.storage.neo4j.node_properties import NodeHydration
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.orchestration.kedro.run_parameters import NukeAllOutsideDevError
from ragcore.orchestration.kedro.run_plan import plan_run

PARAMS: dict[str, Any] = {
    "chunking": {"size": 384, "overlap": 25},
    "embedding": {"model_name": "un-modele", "dimension": 768},
    "embedding_runtime": {"enabled": True},
    "exportation": {
        "skip_unconfigured": False,
        "neo4j": {
            "include_path": True,
            "include_content": True,
            "labels": {"default": "Document", "by_prefix": {"LEGIARTI": "Article"}},
        },
    },
    "maintenance": {"nuke_all": False},
}
"""Les clés de `parameters.yml` sans défaut dans le code."""

BOOLEAN_PATHS = [
    "exportation.skip_unconfigured",
    "embedding_runtime.enabled",
    "exportation.neo4j.include_path",
    "exportation.neo4j.include_content",
    "maintenance.nuke_all",
]
"""Les booléens du YAML : stricts, obligatoires, validés dans tous les environnements."""


def _settings(environment: str = "prod") -> InfraSettings:
    return InfraSettings(
        source="all", environment=environment, qdrant_collection="chunks"
    )


def _cli(**params: str) -> dict[str, object]:
    """Les `run_params` que Kedro 1.x passe au hook : les `--params` sous
    `runtime_params`."""
    return {"runtime_params": params}


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
    plan = plan_run(PARAMS, _settings(), {})

    assert plan.context_source is None, "un run multi-source n'a pas de source"
    assert plan.collection == "chunks"
    assert (plan.chunking.size, plan.chunking.overlap) == (384, 25)
    assert plan.embedding.dimension == 768


@pytest.mark.parametrize("block", ["chunking", "embedding"])
def test_sans_reglage_de_traitement_le_run_s_arrete(block: str) -> None:
    with pytest.raises(ValueError, match=f"`{block}` est absent"):
        plan_run(_without(block), _settings(), {})


def test_un_reglage_de_traitement_mal_forme_arrete_le_run() -> None:
    params = _with("chunking", {"size": 0, "overlap": 25})

    with pytest.raises(ValueError, match="size"):
        plan_run(params, _settings(), {})


def test_un_run_restreint_garde_sa_source() -> None:
    plan = plan_run(PARAMS, _settings(), _cli(source="cass"))

    assert plan.sources == (SourceName.CASS,)
    assert plan.context_source is SourceName.CASS


def test_une_source_inconnue_echoue_avant_d_ouvrir_quoi_que_ce_soit() -> None:
    with pytest.raises(ValueError, match="Source inconnue"):
        plan_run(PARAMS, _settings(), _cli(source="cas"))


@pytest.mark.parametrize("path", BOOLEAN_PATHS)
def test_sans_booleen_le_run_s_arrete_meme_hors_dev(path: str) -> None:
    with pytest.raises(ValueError, match=f"`{path}` est absent"):
        plan_run(_without(path), _settings("prod"), {})


@pytest.mark.parametrize("value", [None, "false", 0])
@pytest.mark.parametrize("path", BOOLEAN_PATHS)
def test_un_booleen_mal_type_arrete_le_run_meme_hors_dev(
    path: str, value: object
) -> None:
    """``"false"`` est une chaîne non vide : lue avec ``bool(...)``, elle vaudrait vrai."""
    with pytest.raises(ValueError, match=f"`{path}` est absent"):
        plan_run(_with(path, value), _settings("prod"), {})


@pytest.mark.parametrize("value", [True, False])
def test_le_curseur_des_balises_non_configurees_vient_du_yaml_en_dev(
    value: bool,
) -> None:
    params = _with("exportation.skip_unconfigured", value)

    assert plan_run(params, _settings("dev"), {}).skip_unconfigured is value


def test_hors_dev_les_balises_non_configurees_sont_toujours_retirees() -> None:
    params = _with("exportation.skip_unconfigured", False)

    assert plan_run(params, _settings("prod"), {}).skip_unconfigured is True


def test_couper_l_embedding_n_a_d_effet_qu_en_dev() -> None:
    params = _with("embedding_runtime.enabled", False)

    assert plan_run(params, _settings("prod"), {}).embedding_enabled
    assert not plan_run(params, _settings("dev"), {}).embedding_enabled


def test_l_hydratation_neo4j_vient_du_yaml_en_dev() -> None:
    params = _with("exportation.neo4j.include_path", False)

    hydration = plan_run(params, _settings("dev"), {}).node_hydration

    assert (hydration.include_path, hydration.include_content) == (False, True)


def test_hors_dev_le_noeud_neo4j_reste_maigre() -> None:
    assert plan_run(PARAMS, _settings("prod"), {}).node_hydration == NodeHydration()


def test_nuke_all_est_refuse_hors_dev_avant_tout_noeud() -> None:
    with pytest.raises(NukeAllOutsideDevError, match="ENVIRONMENT='prod'"):
        plan_run(_with("maintenance.nuke_all", True), _settings("prod"), {})


def test_nuke_all_est_accepte_en_dev() -> None:
    params = _with("maintenance.nuke_all", True)

    assert plan_run(params, _settings("dev"), {}).nuke_all is True


def test_sans_nuke_all_un_run_hors_dev_passe() -> None:
    assert plan_run(PARAMS, _settings("prod"), {}).nuke_all is False


def test_les_labels_neo4j_viennent_du_yaml_par_prefixe_d_identifiant() -> None:
    labels = plan_run(PARAMS, _settings(), {}).node_labels

    assert labels.label_for(Identifier(raw="LEGIARTI000006419264")) == "Article"
    assert labels.label_for(Identifier(raw="JURITEXT000019333891")) == "Document"
    assert labels.known == ("Document", "Article")


def test_sans_labels_neo4j_le_run_s_arrete() -> None:
    with pytest.raises(ValueError, match=r"exportation\.neo4j\.labels"):
        plan_run(_without("exportation.neo4j.labels"), _settings(), {})


@pytest.mark.parametrize(
    ("labels", "message"),
    [
        ({"default": "Document", "by_prefix": {"ARTI": "Article"}}, "Préfixe"),
        ({"default": "Document", "by_prefix": {"LEGIARTI": "Mon Label"}}, "Label"),
        ({"default": "Pending", "by_prefix": {}}, "réservé"),
    ],
)
def test_un_label_ou_un_prefixe_mal_forme_arrete_le_run(
    labels: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        plan_run(_with("exportation.neo4j.labels", labels), _settings(), {})
