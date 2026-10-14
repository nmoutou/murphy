"""Le vocabulaire de ``MURPHY_META.statistics`` (ADR-034 §8) : les chemins des mesures et
les noms des étapes du run.
"""

from time import perf_counter

from ragcore.core.models.enums import SourceName
from ragcore.core.models.run_measures import MeasurePath

__all__ = [
    "CHUNKS",
    "CONTENT_CHARS",
    "FACETS",
    "RELATIONS",
    "STAGE_PHASE1",
    "STAGE_PHASE2_WRITE",
    "STEP_EMBED",
    "STEP_MONGO",
    "STEP_NEO4J",
    "STEP_OPENSEARCH",
    "STEP_PARSE",
    "XML_BYTES",
    "document_measure",
    "milliseconds_since",
    "step_measure",
]

_MS_PER_S = 1000

_DOCUMENTS = "documents"
_STEP_MS = "step_ms"

XML_BYTES = "xml_bytes"
FACETS = "facets"
CONTENT_CHARS = "content_chars"
CHUNKS = "chunks"
RELATIONS = "relations"

STEP_PARSE = "parse"
STEP_EMBED = "embed"
STEP_MONGO = "mongo"
STEP_OPENSEARCH = "opensearch"
STEP_NEO4J = "neo4j"

STAGE_PHASE1 = "phase1"
STAGE_PHASE2_WRITE = "phase2_write"


def document_measure(source: SourceName, name: str) -> MeasurePath:
    return (_DOCUMENTS, source.value, name)


def step_measure(source: SourceName, step: str) -> MeasurePath:
    """En millisecondes, par document."""
    return (_DOCUMENTS, source.value, _STEP_MS, step)


def milliseconds_since(started: float) -> float:
    """``started`` vient de ``time.perf_counter()``."""
    return (perf_counter() - started) * _MS_PER_S
