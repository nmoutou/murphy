"""Doublures en mémoire, pour tester sans Mongo, Neo4j ni OpenSearch. Hors du paquet de
production, qui ne les exécuterait jamais.
"""

from .embedder import NoopEmbedder
from .repositories import (
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryPendingRepository,
    InMemorySearchIndex,
    InMemoryUnformattedRepository,
)
from .runtime import FakeRuntime, FakeRuntimeFactory
from .telemetry import RecordingTelemetry, RecordingTelemetryFactory

__all__ = [
    "FakeRuntime",
    "FakeRuntimeFactory",
    "InMemoryDocumentRepository",
    "InMemoryGraphRepository",
    "InMemoryPendingRepository",
    "InMemorySearchIndex",
    "InMemoryUnformattedRepository",
    "NoopEmbedder",
    "RecordingTelemetry",
    "RecordingTelemetryFactory",
]
