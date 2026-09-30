"""Le plan du run : dérivé une fois, en tête de run, sans rien ouvrir."""

from typing import Any

import pytest

from ragcore.adapters.config.settings import InfraSettings
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.orchestration.kedro.run_plan import plan_run

PROCESSING: dict[str, Any] = {
    "chunking": {"size": 384, "overlap": 25},
    "embedding": {"model_name": "un-modele", "dimension": 768},
}
PARAMS: dict[str, Any] = {
    **PROCESSING,
    "exportation": {
        "skip_unconfigured": False,
        "neo4j": {
            "labels": {"default": "Document", "by_prefix": {"LEGIARTI": "Article"}}
        },
    },
}
"""Les blocs de `parameters.yml` sans défaut dans le code."""


def _settings(environment: str = "prod") -> InfraSettings:
    return InfraSettings(
        source="all", environment=environment, qdrant_collection="chunks"
    )


def _cli(**params: str) -> dict[str, object]:
    """Les `run_params` que Kedro 1.x passe au hook : les `--params` sous
    `runtime_params`."""
    return {"runtime_params": params}


def test_un_run_nu_ecrit_la_collection_configuree() -> None:
    plan = plan_run(PARAMS, _settings(), {})

    assert plan.context_source is None, "un run multi-source n'a pas de source"
    assert plan.collection == "chunks"
    assert (plan.chunking.size, plan.chunking.overlap) == (384, 25)
    assert plan.embedding.dimension == 768


@pytest.mark.parametrize("block", ["chunking", "embedding"])
def test_sans_reglage_de_traitement_le_run_s_arrete(block: str) -> None:
    params = {name: value for name, value in PARAMS.items() if name != block}

    with pytest.raises(ValueError, match=f"`{block}` est absent"):
        plan_run(params, _settings(), {})


def test_un_reglage_de_traitement_mal_forme_arrete_le_run() -> None:
    params = {**PARAMS, "chunking": {"size": 0, "overlap": 25}}

    with pytest.raises(ValueError, match="size"):
        plan_run(params, _settings(), {})


def test_un_run_restreint_garde_sa_source() -> None:
    plan = plan_run(PARAMS, _settings(), _cli(source="cass"))

    assert plan.sources == (SourceName.CASS,)
    assert plan.context_source is SourceName.CASS


def test_une_source_inconnue_echoue_avant_d_ouvrir_quoi_que_ce_soit() -> None:
    with pytest.raises(ValueError, match="Source inconnue"):
        plan_run(PARAMS, _settings(), _cli(source="cas"))


def test_couper_l_embedding_n_a_d_effet_qu_en_dev() -> None:
    params = {**PARAMS, "embedding_runtime": {"enabled": False}}

    assert plan_run(params, _settings("prod"), {}).embedding_enabled
    assert not plan_run(params, _settings("dev"), {}).embedding_enabled


def _with_skip_unconfigured(value: object) -> dict[str, Any]:
    return {
        **PARAMS,
        "exportation": {**PARAMS["exportation"], "skip_unconfigured": value},
    }


@pytest.mark.parametrize("value", [True, False])
def test_le_curseur_des_balises_non_configurees_vient_du_yaml(value: bool) -> None:
    assert (
        plan_run(_with_skip_unconfigured(value), _settings(), {}).skip_unconfigured
        is value
    )


def test_sans_curseur_des_balises_non_configurees_le_run_s_arrete() -> None:
    exportation = {
        name: value
        for name, value in PARAMS["exportation"].items()
        if name != "skip_unconfigured"
    }

    with pytest.raises(ValueError, match=r"exportation\.skip_unconfigured"):
        plan_run({**PARAMS, "exportation": exportation}, _settings(), {})


@pytest.mark.parametrize("value", [None, "false", "skip", 0])
def test_un_curseur_non_booleen_arrete_le_run(value: object) -> None:
    """``"false"`` est une chaîne non vide : lue avec ``bool(...)``, elle vaudrait vrai."""
    with pytest.raises(ValueError, match=r"exportation\.skip_unconfigured"):
        plan_run(_with_skip_unconfigured(value), _settings(), {})


def test_les_labels_neo4j_viennent_du_yaml_par_prefixe_d_identifiant() -> None:
    labels = plan_run(PARAMS, _settings(), {}).node_labels

    assert labels.label_for(Identifier(raw="LEGIARTI000006419264")) == "Article"
    assert labels.label_for(Identifier(raw="JURITEXT000019333891")) == "Document"
    assert labels.known == ("Document", "Article")


def test_sans_labels_neo4j_le_run_s_arrete() -> None:
    with pytest.raises(ValueError, match=r"exportation\.neo4j\.labels"):
        plan_run(PROCESSING, _settings(), {})


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
    params = {**PROCESSING, "exportation": {"neo4j": {"labels": labels}}}

    with pytest.raises(ValueError, match=message):
        plan_run(params, _settings(), {})
