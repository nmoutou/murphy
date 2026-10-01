"""Le node `parse_documents` ne range en `parse_error` que ce que le port promet.

Le contrat de ``BaseParser`` : ``ValidationError`` si le document est irrecevable,
``ParseError`` s'il est illisible. Le node rattrapait tout ``Exception`` comme une
« autre erreur de parsing » : un bug du run (un document qu'aucun parser ne sait
router) devenait un rejet PAR DOCUMENT, compté et exclu en silence. Il remonte
désormais, et arrête le run.
"""

from datetime import UTC, datetime
from xml.etree import ElementTree as ET

import pytest

from ragcore.application.run_context import PipelineContext
from ragcore.core.exceptions import ParseError
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally
from ragcore.core.ports.parser import ParseResult
from ragcore.core.services.exclusion_reasons import REASON_PARSE_ERROR
from ragcore.core.services.unknown_categories import CATEGORY_TAG
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED
from ragcore.orchestration.kedro.nodes.parse_documents import parse_documents_node
from ragcore.sources.generic import GenericParser, to_tree
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE
from ragcore.tests.fakes.telemetry import RecordingTelemetry

_SOURCE_FILE = "LEGIARTI000000000001.xml"
_UNRENAMED_KEY = "article_meta_meta_spec_meta_article_derniere_modification"
_ARTICLE_WITH_UNRENAMED_META = (
    "<ARTICLE><META>"
    "<META_COMMUN><ID>LEGIARTI000000000001</ID><ORIGINE>LEGI</ORIGINE></META_COMMUN>"
    "<META_SPEC><META_ARTICLE>"
    "<DERNIERE_MODIFICATION>2020-01-01</DERNIERE_MODIFICATION>"
    "</META_ARTICLE></META_SPEC>"
    "</META></ARTICLE>"
)


class _FailingParser:
    """Parser idiot : lève l'exception qu'on lui donne, pour chaque document."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def parse(self, raw: RawDocument) -> ParseResult:
        del raw
        raise self._error


def _raw_document() -> RawDocument:
    return RawDocument(
        source=SourceName.LEGI,
        source_document_id="doc-1",
        payload={},
        fetched_at=datetime.now(UTC),
    )


def _run(parser: _FailingParser, telemetry: RecordingTelemetry) -> list[str]:
    _, to_skip = parse_documents_node(
        raw_documents=[_raw_document()],
        parser=parser,
        pipeline_context=PipelineContext.create(),
        telemetry=telemetry,
        skip_unconfigured=False,
    )
    return to_skip


def test_une_ParseError_exclut_le_document_et_le_compte() -> None:
    telemetry = RecordingTelemetry()

    to_skip = _run(_FailingParser(ParseError("XML malformé")), telemetry)

    assert to_skip == ["doc-1"]
    invalidated = telemetry.events_of(DOCUMENT_INVALIDATED)
    assert [e.payload["reason"] for e in invalidated] == [REASON_PARSE_ERROR]


def test_une_exception_HORS_contrat_arrete_le_run() -> None:
    """Le cas réel : ``RoutingParser`` lève ``ValueError`` pour un document qu'aucun
    parser ne sait router. Ce n'est pas un document illisible, c'est un bug du run."""
    telemetry = RecordingTelemetry()

    with pytest.raises(ValueError, match="Aucun parser"):
        _run(_FailingParser(ValueError("Aucun parser pour 'cass'")), telemetry)

    assert telemetry.events_of(DOCUMENT_INVALIDATED) == [], (
        "le document n'est pas exclu en silence"
    )


def _parse_article(skip_unconfigured: bool, telemetry: RecordingTelemetry):
    raw = RawDocument(
        source=SourceName.LEGI,
        source_document_id="doc-1",
        payload={
            "content": [to_tree(ET.fromstring(_ARTICLE_WITH_UNRENAMED_META))],
            "files": [_SOURCE_FILE],
        },
        fetched_at=datetime.now(UTC),
    )
    to_process, _ = parse_documents_node(
        raw_documents=[raw],
        parser=GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI),
        pipeline_context=PipelineContext.create(),
        telemetry=telemetry,
        skip_unconfigured=skip_unconfigured,
    )
    return to_process[0]


@pytest.mark.parametrize("skip_unconfigured", [True, False])
def test_une_balise_sans_renommage_est_SIGNALEE_dans_les_deux_cas(
    skip_unconfigured: bool,
) -> None:
    telemetry = RecordingTelemetry()

    _parse_article(skip_unconfigured, telemetry)

    example = UnknownExample(
        identifier="LEGIARTI000000000001", source_file=_SOURCE_FILE
    )
    assert telemetry.snapshot().unknowns == {
        CATEGORY_TAG: {_UNRENAMED_KEY: UnknownTally(count=1, example=example)}
    }


def test_skip_RETIRE_la_metadonnee_sans_renommage_et_garde_les_autres() -> None:
    parsed = _parse_article(skip_unconfigured=True, telemetry=RecordingTelemetry())

    assert _UNRENAMED_KEY not in parsed.metadata
    assert parsed.metadata["origine"] == "LEGI"


def test_sans_skip_la_metadonnee_sans_renommage_est_INGEREE() -> None:
    parsed = _parse_article(skip_unconfigured=False, telemetry=RecordingTelemetry())

    assert parsed.metadata[_UNRENAMED_KEY] == "2020-01-01"
