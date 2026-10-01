"""Les ports sont des Protocol @runtime_checkable : la conformité est
structurelle, aucune implémentation n'hérite du port. Ces tests la vérifient
donc à l'exécution — sinon rien ne la vérifierait du tout.

Les ports ont été reconstruits d'après leurs appelants. Que les implémentations
survivantes les satisfassent est la preuve que la reconstruction est fidèle.
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
            "ragcore.adapters.telemetry.registry_aware",
            "RegistryAwareTelemetry",
            TelemetryPort,
        ),
        ("ragcore.adapters.telemetry.noop", "NoopTelemetry", TelemetryPort),
        # Le parser et le chunker sont GÉNÉRIQUES : un seul de chacun, pour six sources.
        # `sources/legislatif/` n'apporte plus qu'une table et un extracteur-coquille.
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
    # __new__ sans __init__ : on teste la forme de la classe, pas sa construction
    # (plusieurs de ces adapters exigent une connexion en argument).
    assert isinstance(cls.__new__(cls), port)


def test_a_class_missing_a_method_does_not_satisfy_the_port() -> None:
    """Sans ce contre-exemple, les assertions ci-dessus pourraient toutes passer
    parce que le Protocol ne vérifie rien.
    """

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
