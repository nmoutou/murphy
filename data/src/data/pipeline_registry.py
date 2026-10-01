"""Délègue au registre de ragcore."""

from kedro.pipeline import Pipeline

from ragcore.orchestration.kedro.pipeline_registry import (
    register_pipelines as _ragcore_register_pipelines,
)


def register_pipelines() -> dict[str, Pipeline]:
    return _ragcore_register_pipelines()
