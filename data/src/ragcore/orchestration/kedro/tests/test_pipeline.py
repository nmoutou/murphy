"""Le DAG — sa forme, et les deux arêtes qui portent tout son sens.

Un pipeline Kedro n'est correct que si ses dépendances de données EXPRIMENT l'ordre
voulu. Deux arêtes ne sont pas décoratives, et ce fichier les exécute :

- ``force_drop_done`` → ``connect`` : on n'ouvre pas la source pendant qu'on efface.
- ``ingestion_outcome`` → ``resolveRelations`` : LA barrière phase-1/phase-2. Sans
  elle, la phase 2 écrirait des arêtes vers des nœuds pas encore créés.

Et la porte : ``register_pipelines`` est le premier code ragcore que Kedro exécute.
S'il ne s'importe pas, rien ne tourne.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline

from ragcore.orchestration.kedro.pipeline import create_ingestion_pipeline
from ragcore.orchestration.kedro.pipeline_registry import register_pipelines


def _pipeline() -> Pipeline:
    return create_ingestion_pipeline()


def _inputs(pipeline: Pipeline, node_name: str) -> set[str]:
    (node,) = (n for n in pipeline.nodes if n.name == node_name)
    return set(node.inputs)


def test_la_porte_repond_et_rend_des_pipelines() -> None:
    """``register_pipelines`` est LA porte : ``data/pipeline_registry.py`` l'importe.

    Tant que ce module n'existait pas, ``kedro run`` échouait à l'import — avant même
    de construire un nœud.
    """
    pipelines = register_pipelines()

    assert set(pipelines) == {"__default__", "ingestion"}
    assert all(isinstance(p, Pipeline) for p in pipelines.values())
    # Un alias, pas deux pipelines distincts.
    assert pipelines["__default__"] is pipelines["ingestion"]


def test_les_sept_noeuds_sont_la() -> None:
    names = {n.name for n in _pipeline().nodes}

    assert names == {
        "cleanup",
        "forceDrop",
        "connect",
        "computeIdempotence",
        "ingest",
        "resolveRelations",
        "report",
    }


def test_la_barriere_phase1_phase2_est_une_arete() -> None:
    """``resolveRelations`` consomme l'outcome d'``ingest`` : Kedro ne peut donc pas
    l'ordonnancer avant que la phase 1 ait fini pour TOUS les documents.
    """
    pipeline = _pipeline()

    assert "ingestion_outcome" in _inputs(pipeline, "resolveRelations")
    # Et c'est bien ``ingest`` qui le produit.
    (ingest,) = (n for n in pipeline.nodes if n.name == "ingest")
    assert "ingestion_outcome" in set(ingest.outputs)


def test_forceDrop_precede_connect() -> None:
    """``connect`` prend ``force_drop_done`` en input signal-only : on n'ouvre pas la
    source pendant qu'on efface les stores.
    """
    pipeline = _pipeline()

    assert "force_drop_done" in _inputs(pipeline, "connect")
    (force_drop,) = (n for n in pipeline.nodes if n.name == "forceDrop")
    assert "force_drop_done" in set(force_drop.outputs)


def test_le_report_est_terminal() -> None:
    """``report`` consomme les deux outcomes : c'est le confluent des deux phases, et
    rien ne dépend de lui.
    """
    pipeline = _pipeline()
    report_inputs = _inputs(pipeline, "report")

    assert {"ingestion_outcome", "resolution_outcome"} <= report_inputs
    # Rien ne consomme ``run_report`` : le report est bien une feuille du DAG.
    consumed = {i for n in pipeline.nodes for i in n.inputs}
    assert "run_report" not in consumed


def test_le_pipeline_est_un_DAG_coherent() -> None:
    """Kedro refuse à la construction un graphe cyclique ou dont un input n'a pas de
    producteur parmi les nœuds ou le catalogue. Le fait que ``create_ingestion_pipeline``
    ait RÉUSSI est déjà une preuve ; on vérifie ici qu'il y a bien un ordre topologique.
    """
    pipeline = _pipeline()

    # ``nodes`` est renvoyé dans l'ordre topologique par Kedro : le premier ne dépend
    # d'aucun autre nœud, le dernier de la chaîne complète.
    ordered = [n.name for n in pipeline.nodes]
    assert ordered.index("ingest") < ordered.index("resolveRelations")
    assert ordered.index("resolveRelations") < ordered.index("report")
    assert ordered.index("forceDrop") < ordered.index("connect")
