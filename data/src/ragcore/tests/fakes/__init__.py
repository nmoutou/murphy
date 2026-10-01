"""Doublures en mémoire — le lot 2 se vérifie sans Mongo, sans Neo4j, sans Qdrant.

Elles vivent sous ``tests/`` et non sous ``adapters/`` : un dépôt en mémoire livré
dans le package de production serait du code que la production n'exécute jamais.
"""

from .embedder import NoopEmbedder
from .repositories import (
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryPendingRepository,
    InMemoryVectorRepository,
)
from .runtime import FakeRuntime, FakeRuntimeFactory
from .telemetry import RecordingTelemetry, RecordingTelemetryFactory

__all__ = [
    "FakeRuntime",
    "FakeRuntimeFactory",
    "InMemoryDocumentRepository",
    "InMemoryGraphRepository",
    "InMemoryPendingRepository",
    "InMemoryVectorRepository",
    "NoopEmbedder",
    "RecordingTelemetry",
    "RecordingTelemetryFactory",
]
