"""Doublures en mémoire, pour tester sans Mongo, Neo4j ni Qdrant. Hors du paquet de
production, qui ne les exécuterait jamais.
"""

from .embedder import NoopEmbedder
from .repositories import (
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryPendingRepository,
    InMemoryUnformattedRepository,
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
    "InMemoryUnformattedRepository",
    "InMemoryVectorRepository",
    "NoopEmbedder",
    "RecordingTelemetry",
    "RecordingTelemetryFactory",
]
