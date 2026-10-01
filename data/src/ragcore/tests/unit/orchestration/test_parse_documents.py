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
from ragcore.core.models.collision import Collision
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally
from ragcore.core.ports.parser import ParseResult
from ragcore.core.services.exclusion_reasons import REASON_COLLISION, REASON_PARSE_ERROR
from ragcore.core.services.unknown_categories import CATEGORY_COLLISION, CATEGORY_TAG
from ragcore.core.telemetry_events import (
    COLLISION_UNRECORDED,
    DOCUMENT_INVALIDATED,
)
from ragcore.orchestration.kedro.nodes.parse_documents import parse_documents_node
from ragcore.sources.generic import GenericParser, to_tree
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE
from ragcore.tests.fakes.repositories import InMemoryCollisionRepository
from ragcore.tests.fakes.runtime import FakeRuntime
from ragcore.tests.fakes.telemetry import RecordingTelemetry

_SOURCE_FILE = "LEGIARTI000000000001.xml"
_UNRENAMED_KEY = "article_meta_meta_spec_meta_article_ministere"
_ARTICLE_WITH_UNRENAMED_META = (
    "<ARTICLE><META>"
    "<META_COMMUN><ID>LEGIARTI000000000001</ID><ORIGINE>LEGI</ORIGINE></META_COMMUN>"
    "<META_SPEC><META_ARTICLE>"
    "<MINISTERE>Justice</MINISTERE>"
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
        collision_repo=InMemoryCollisionRepository(),
        pipeline_runtime=FakeRuntime(worker_id=-1),
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
        collision_repo=InMemoryCollisionRepository(),
        pipeline_runtime=FakeRuntime(worker_id=-1),
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

    assert parsed.metadata[_UNRENAMED_KEY] == "Justice"


# ── Collisions de métadonnées (ADR-049) ───────────────────────────────────────


def _article(identifier: str, metadata: str) -> RawDocument:
    xml = (
        f"<ARTICLE><META><META_COMMUN><ID>{identifier}</ID>{metadata}</META_COMMUN>"
        "</META></ARTICLE>"
    )
    return RawDocument(
        source=SourceName.LEGI,
        source_document_id=identifier,
        payload={"content": [to_tree(ET.fromstring(xml))], "files": [_SOURCE_FILE]},
        fetched_at=datetime.now(UTC),
    )


_LISTED = _article("LEGIARTI000000000002", "<URL>a</URL><URL>b</URL>")
_REFUSED = _article("LEGIARTI000000000003", "<NUM>1</NUM><NUM>2</NUM>")


def _parse_collisions(
    repository: InMemoryCollisionRepository, telemetry: RecordingTelemetry
) -> tuple[list[str], list[str]]:
    to_process, to_skip = parse_documents_node(
        raw_documents=[_LISTED, _REFUSED],
        parser=GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI),
        pipeline_context=PipelineContext.create(),
        telemetry=telemetry,
        skip_unconfigured=True,
        collision_repo=repository,
        pipeline_runtime=FakeRuntime(worker_id=-1),
    )
    return [parsed.identifier.raw for parsed in to_process], to_skip


def test_une_collision_non_configuree_est_rejetee_sous_sa_raison() -> None:
    telemetry = RecordingTelemetry()

    parsed, skipped = _parse_collisions(InMemoryCollisionRepository(), telemetry)

    assert parsed == ["LEGIARTI000000000002"]
    assert skipped == ["LEGIARTI000000000003"]
    invalidated = telemetry.events_of(DOCUMENT_INVALIDATED)
    assert [e.payload["reason"] for e in invalidated] == [REASON_COLLISION]


def test_le_bilan_et_la_collection_CONCORDENT() -> None:
    """Parsé ou refusé, chaque (document, clé) en collision est compté une fois au
    bilan et écrit une fois dans la collection."""
    repository = InMemoryCollisionRepository()
    telemetry = RecordingTelemetry()

    _parse_collisions(repository, telemetry)

    tallies = telemetry.snapshot().unknowns[CATEGORY_COLLISION]
    recorded: list[Collision] = [collision for _, collision in repository.records]
    assert {key: tally.count for key, tally in tallies.items()} == {"url": 1, "num": 1}
    assert sorted(collision.key for collision in recorded) == ["num", "url"]


def test_une_ecriture_ratee_degrade_le_run_sans_l_arreter() -> None:
    telemetry = RecordingTelemetry()

    parsed, _ = _parse_collisions(
        InMemoryCollisionRepository(is_failing=True), telemetry
    )

    assert parsed == ["LEGIARTI000000000002"]
    assert len(telemetry.events_of(COLLISION_UNRECORDED)) == 1
