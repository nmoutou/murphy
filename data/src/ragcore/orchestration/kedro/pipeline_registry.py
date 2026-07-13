"""Le registre des pipelines — LA PORTE que le projet Kedro importe.

``data/src/data/pipeline_registry.py`` délègue ici : ``register_pipelines()`` est le
premier code ragcore que Kedro exécute. Tant que ce module n'existait pas, ``kedro
run`` échouait à l'import, avant même de construire le moindre nœud. C'est l'analogue
exact du ``file_connector`` manquant du lot 4 : une porte fermée en amont de tout.

Il n'y a qu'un pipeline, exposé sous deux noms : ``__default__`` (ce que Kedro lance
sans argument) et ``ingestion`` (le nom explicite). Un alias, pas deux pipelines.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline

from .pipeline import create_ingestion_pipeline

__all__ = ["register_pipelines"]


def register_pipelines() -> dict[str, Pipeline]:
    """Enregistre les pipelines du projet."""
    ingestion = create_ingestion_pipeline()
    return {
        "__default__": ingestion,
        "ingestion": ingestion,
    }
