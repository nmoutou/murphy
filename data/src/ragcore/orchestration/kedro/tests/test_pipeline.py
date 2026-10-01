"""Le DAG : sa forme, et les deux arêtes qui portent l'ordre.

- ``nuke_done`` → ``connect`` : la source n'est pas lue pendant l'effacement ;
- ``ingestion_outcome`` → ``resolveRelations`` : la barrière entre les phases.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from kedro.pipeline import Pipeline

from ragcore.orchestration.kedro.pipeline import create_ingestion_pipeline
from ragcore.orchestration.kedro.pipeline_registry import register_pipelines

_CATALOG = Path(__file__).parents[5] / "conf" / "base" / "catalog.yml"


def _pipeline() -> Pipeline:
    return create_ingestion_pipeline()


def _inputs(pipeline: Pipeline, node_name: str) -> set[str]:
    (node,) = (n for n in pipeline.nodes if n.name == node_name)
    return set(node.inputs)


def test_la_porte_repond_et_rend_des_pipelines() -> None:
    """``data/pipeline_registry.py`` l'importe : sans lui, ``kedro run`` échoue à
    l'import."""
    pipelines = register_pipelines()

    assert set(pipelines) == {"__default__", "ingestion"}
    assert all(isinstance(p, Pipeline) for p in pipelines.values())
    # Un alias, pas deux pipelines
    assert pipelines["__default__"] is pipelines["ingestion"]


def test_les_six_noeuds_sont_la() -> None:
    names = {n.name for n in _pipeline().nodes}

    assert names == {
        "nukeAll",
        "connect",
        "parseDocuments",
        "ingest",
        "resolveRelations",
        "report",
    }


def test_la_barriere_phase1_phase2_est_une_arete() -> None:
    """La phase 2 attend que la phase 1 ait fini pour tous les documents."""
    pipeline = _pipeline()

    assert "ingestion_outcome" in _inputs(pipeline, "resolveRelations")
    # Et c'est bien `ingest` qui le produit
    (ingest,) = (n for n in pipeline.nodes if n.name == "ingest")
    assert "ingestion_outcome" in set(ingest.outputs)


def test_nukeAll_precede_connect() -> None:
    """La source n'est pas lue pendant l'effacement."""
    pipeline = _pipeline()

    assert "nuke_done" in _inputs(pipeline, "connect")
    (nuke_all,) = (n for n in pipeline.nodes if n.name == "nukeAll")
    assert "nuke_done" in set(nuke_all.outputs)


def test_le_report_est_terminal() -> None:
    """``report`` est le confluent des deux phases, et rien n'en dépend."""
    pipeline = _pipeline()
    report_inputs = _inputs(pipeline, "report")

    assert {"ingestion_outcome", "resolution_outcome"} <= report_inputs
    # Rien ne consomme `run_report` : une feuille du DAG
    consumed = {i for n in pipeline.nodes for i in n.inputs}
    assert "run_report" not in consumed


def test_le_pipeline_est_un_DAG_coherent() -> None:
    """Kedro a accepté le graphe ; on vérifie l'ordre topologique."""
    pipeline = _pipeline()

    # Kedro rend les nœuds dans l'ordre topologique
    ordered = [n.name for n in pipeline.nodes]
    assert ordered.index("ingest") < ordered.index("resolveRelations")
    assert ordered.index("resolveRelations") < ordered.index("report")
    assert ordered.index("nukeAll") < ordered.index("connect")


def test_chaque_input_venu_du_hook_est_declare_au_catalogue() -> None:
    """Un input qu'aucun nœud ne produit vient du hook : sans entrée ``MemoryDataset``
    dans ``catalog.yml``, Kedro refuse le run au démarrage."""
    pipeline = _pipeline()
    produced = {output for node in pipeline.nodes for output in node.outputs}
    external = {i for n in pipeline.nodes for i in n.inputs} - produced
    declared = set(yaml.safe_load(_CATALOG.read_text(encoding="utf-8")))

    assert external <= declared, f"Absents du catalogue : {external - declared}"
