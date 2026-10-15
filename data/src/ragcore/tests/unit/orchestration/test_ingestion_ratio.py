"""``ingestion_ratio`` : une part par source, validée et résolue par le plan du run."""

import logging
import re
from typing import Any

import pytest

from ragcore.adapters.config.settings import Environment, InfraSettings
from ragcore.core.models.enums import SourceName
from ragcore.core.models.processing import ChunkingConfig
from ragcore.orchestration.kedro.run_plan import RunPlan, plan_run

CHUNKING = ChunkingConfig(max_chars=384, overlap_chars=25)

FLAGS: dict[str, Any] = {
    "nuke_all": False,
    "embedding_enabled": True,
    "skip_unconfigured": False,
    "include_path": True,
    "include_content_neo4j": True,
}


def _plan(
    ratios: object, source: str = "legi,cass", environment: Environment = "dev"
) -> RunPlan:
    settings = InfraSettings(
        source=source, environment=environment, opensearch_index="documents"
    )
    return plan_run({**FLAGS, "ingestion_ratio": ratios}, settings, CHUNKING)


def _path(path: str) -> str:
    return re.escape(f"`{path}`")


def test_une_source_absente_de_la_table_est_ingeree_en_entier() -> None:
    plan = _plan({"legi": 0.25})

    assert plan.ingestion_ratios == {SourceName.LEGI: 0.25, SourceName.CASS: 1}


def test_une_table_vide_ingere_tout() -> None:
    plan = _plan({})

    assert plan.ingestion_ratios == {SourceName.LEGI: 1, SourceName.CASS: 1}


def test_une_source_a_0_sort_du_run(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        plan = _plan({"cass": 0})

    assert plan.sources == (SourceName.LEGI,)
    assert plan.ingestion_ratios == {SourceName.LEGI: 1}
    assert "SOURCES ÉCARTÉES" in caplog.text
    assert "cass" in caplog.text


def test_un_run_dont_toutes_les_sources_sont_a_0_s_arrete() -> None:
    """Sinon un run vide finirait « ok », après `nuke_all`."""
    with pytest.raises(ValueError, match="Rien à ingérer"):
        _plan({"cass": 0}, source="cass")


def test_une_source_a_0_hors_du_run_ne_compte_pas() -> None:
    plan = _plan({"jade": 0}, source="cass")

    assert plan.sources == (SourceName.CASS,)


def test_hors_dev_tout_est_ingere() -> None:
    plan = _plan({"legi": 0.1, "cass": 0}, environment="prod")

    assert plan.ingestion_ratios == {SourceName.LEGI: 1, SourceName.CASS: 1}


@pytest.mark.parametrize("unknown", ["lgi", "jorf", "upload"])
def test_une_source_inconnue_ou_sans_connecteur_arrete_le_run(unknown: str) -> None:
    """Ignorée, la coquille ingérerait la source en entier."""
    with pytest.raises(ValueError, match=f"sources inconnues : {unknown}"):
        _plan({unknown: 0.5}, environment="prod")


@pytest.mark.parametrize("value", [-0.5, 1.5, "0.5", True, None])
def test_un_ratio_hors_de_0_1_arrete_le_run_meme_hors_dev(value: object) -> None:
    with pytest.raises(ValueError, match=_path("ingestion_ratio.cass")):
        _plan({"cass": value}, environment="prod")


@pytest.mark.parametrize("value", [0.5, 1, None])
def test_un_ratio_hors_table_arrete_le_run(value: object) -> None:
    with pytest.raises(ValueError, match=_path("ingestion_ratio")):
        _plan(value, environment="prod")


def test_sans_ratio_le_run_s_arrete() -> None:
    settings = InfraSettings(environment="prod", opensearch_index="documents")

    with pytest.raises(ValueError, match=_path("ingestion_ratio")):
        plan_run(FLAGS, settings, CHUNKING)


def test_un_run_partiel_est_annonce(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        _plan({"legi": 0.25})

    assert "INGESTION PARTIELLE" in caplog.text
    assert "legi=0.25" in caplog.text


def test_un_run_complet_n_annonce_rien(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        _plan({"legi": 1})

    assert "INGESTION PARTIELLE" not in caplog.text
    assert "SOURCES ÉCARTÉES" not in caplog.text
