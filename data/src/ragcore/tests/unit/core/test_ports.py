"""Les ports sont des Protocol ``@runtime_checkable`` : la conformité est structurelle,
vérifiée ici à l'exécution.
"""

import importlib

import pytest

from ragcore.core.ports.chunker import BaseChunker
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.parser import BaseParser
from ragcore.core.ports.relation_extractor import BaseRelationExtractor
from ragcore.core.ports.telemetry import TelemetryPort


@pytest.mark.parametrize(
    ("module_path", "class_name", "port"),
    [
        (
            "ragcore.adapters.telemetry.console_log",
            "ConsoleLogTelemetry",
            TelemetryPort,
        ),
        ("ragcore.adapters.telemetry.aggregator", "RunStatsAggregator", TelemetryPort),
        (
            "ragcore.adapters.telemetry.worker_stack",
            "WorkerTelemetryStack",
            TelemetryPort,
        ),
        ("ragcore.adapters.telemetry.noop", "NoopTelemetry", TelemetryPort),
        # Parser et chunker génériques : un de chaque pour toutes les sources
        ("ragcore.sources.generic.parser", "GenericParser", BaseParser),
        ("ragcore.sources.generic.chunking", "StructuralChunker", BaseChunker),
        (
            "ragcore.sources.generic.relations",
            "GenericRelationExtractor",
            BaseRelationExtractor,
        ),
    ],
)
def test_implementation_satisfies_its_port(
    module_path: str, class_name: str, port: type
) -> None:
    cls = getattr(importlib.import_module(module_path), class_name)
    # __new__ sans __init__ : la forme de la classe, sans connexion à fournir
    assert isinstance(cls.__new__(cls), port)


def test_a_class_missing_a_method_does_not_satisfy_the_port() -> None:
    """Le contre-exemple : sans lui, le Protocol pourrait ne rien vérifier."""

    class Impostor:
        def emit(self, event) -> None: ...

        # pas de `log`

    assert not isinstance(Impostor(), TelemetryPort)


def test_ports_expose_the_methods_their_callers_call() -> None:
    """Les nœuds Kedro appellent ces méthodes par leur nom."""
    for port, method in [
        (BaseConnector, "fetch_all"),
        (BaseEmbedder, "embed"),
        (BaseParser, "parse"),
        (BaseChunker, "chunk"),
        (BaseRelationExtractor, "extract"),
    ]:
        assert hasattr(port, method), f"{port.__name__}.{method} manquant"
