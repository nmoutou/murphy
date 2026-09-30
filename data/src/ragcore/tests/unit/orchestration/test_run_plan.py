"""Le plan du run : dérivé une fois, en tête de run, sans rien ouvrir."""

from typing import Any

import pytest

from ragcore.adapters.config.settings import InfraSettings
from ragcore.core.config import collection_name
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.orchestration.kedro.run_parameters import build_workflow_config
from ragcore.orchestration.kedro.run_plan import plan_run

PARAMS: dict[str, Any] = {
    "exportation": {
        "neo4j": {
            "labels": {"default": "Document", "by_prefix": {"LEGIARTI": "Article"}}
        }
    }
}
"""Le seul bloc de `parameters.yml` sans défaut dans le code : les labels Neo4j."""


def _settings(environment: str = "prod") -> InfraSettings:
    return InfraSettings(source="all", owner_id="default", environment=environment)


def _cli(**params: str) -> dict[str, object]:
    """Les `run_params` que Kedro 1.x passe au hook : les `--params` sous
    `runtime_params`."""
    return {"runtime_params": params}


def test_un_run_nu_est_complet_et_ecrit_la_collection_derivee() -> None:
    plan = plan_run(PARAMS, _settings(), {})

    assert plan.is_full_run
    assert plan.context_source is None, "un run multi-source n'a pas de source"
    assert plan.collection == collection_name(build_workflow_config(PARAMS))


def test_un_run_restreint_n_est_pas_complet_et_garde_sa_source() -> None:
    plan = plan_run(PARAMS, _settings(), _cli(source="cass"))

    assert plan.sources == (SourceName.CASS,)
    assert not plan.is_full_run
    assert plan.context_source is SourceName.CASS


def test_l_owner_id_de_la_ligne_de_commande_prime_sur_l_environnement() -> None:
    assert plan_run(PARAMS, _settings(), _cli(owner_id="alice")).owner_id == "alice"
    assert plan_run(PARAMS, _settings(), {}).owner_id == "default"


def test_une_source_inconnue_echoue_avant_d_ouvrir_quoi_que_ce_soit() -> None:
    with pytest.raises(ValueError, match="Source inconnue"):
        plan_run(PARAMS, _settings(), _cli(source="cas"))


def test_couper_l_embedding_n_a_d_effet_qu_en_dev() -> None:
    params = {**PARAMS, "embedding_runtime": {"enabled": False}}

    assert plan_run(params, _settings("prod"), {}).embedding_enabled
    assert not plan_run(params, _settings("dev"), {}).embedding_enabled


def test_les_labels_neo4j_viennent_du_yaml_par_prefixe_d_identifiant() -> None:
    labels = plan_run(PARAMS, _settings(), {}).node_labels

    assert labels.label_for(Identifier(raw="LEGIARTI000006419264")) == "Article"
    assert labels.label_for(Identifier(raw="JURITEXT000019333891")) == "Document"
    assert labels.known == ("Document", "Article")


def test_sans_labels_neo4j_le_run_s_arrete() -> None:
    with pytest.raises(ValueError, match=r"exportation\.neo4j\.labels"):
        plan_run({}, _settings(), {})


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
    params = {"exportation": {"neo4j": {"labels": labels}}}

    with pytest.raises(ValueError, match=message):
        plan_run(params, _settings(), {})
