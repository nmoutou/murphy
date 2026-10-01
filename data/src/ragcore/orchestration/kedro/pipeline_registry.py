"""Le registre des pipelines, auquel ``data/src/data/pipeline_registry.py`` délègue.

Un seul pipeline, sous deux noms : ``__default__`` et ``ingestion``.
"""

from __future__ import annotations

from kedro.pipeline import Pipeline

from .pipeline import create_ingestion_pipeline

__all__ = ["register_pipelines"]


def register_pipelines() -> dict[str, Pipeline]:
    ingestion = create_ingestion_pipeline()
    return {
        "__default__": ingestion,
        "ingestion": ingestion,
    }
