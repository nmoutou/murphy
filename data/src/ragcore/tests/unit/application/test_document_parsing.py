"""Le parse ne range en rejet que ce que le port promet (``ValidationError``,
``ParseError``) : toute autre exception est un bug du run, qui l'arrête.
"""

from datetime import UTC, datetime
from xml.etree import ElementTree as ET

import pytest

from ragcore.application.document_parsing import DocumentParsing
from ragcore.application.run_context import PipelineContext
from ragcore.core.exceptions import (
    FacetRootCollisionError,
    ParseError,
    ValidationError,
)
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally
from ragcore.core.ports.parser import ParseResult
from ragcore.core.services.collision_reasons import (
    COLLISION_FACET_ROOT_DUPLICATED,
    COLLISION_METADATA,
)
from ragcore.core.services.exclusion_reasons import (
    REASON_COLLISION,
    REASON_FACET_ROOT_DUPLICATED,
    REASON_PARSE_ERROR,
)
from ragcore.core.services.unknown_categories import CATEGORY_TAG
from ragcore.core.statistics_measures import STEP_PARSE, step_measure
from ragcore.core.telemetry_events import DOCUMENT_INVALIDATED
from ragcore.sources.generic import GenericParser, to_tree
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE
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
    """Lève l'exception donnée, pour chaque document."""

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


def _parse_documents(
    raw_documents: list[RawDocument],
    parser: object,
    telemetry: RecordingTelemetry,
    skip_unconfigured: bool,
) -> tuple[list, list[str]]:
    parsing = DocumentParsing(
        parser,  # type: ignore[arg-type]
        PipelineContext.create(),
        telemetry,
        skip_unconfigured,
    )
    return list(parsing.parse_all(raw_documents)), parsing.skipped


def test_le_parse_est_un_flux() -> None:
    """Un document rejeté n'arrête pas le flux, et rien n'est parsé d'avance."""
    seen: list[str] = []

    def raws():  # noqa: ANN202
        for raw in [_raw_document()]:
            seen.append(raw.source_document_id)
            yield raw

    parsing = DocumentParsing(
        _FailingParser(ParseError("XML malformé")),  # type: ignore[arg-type]
        PipelineContext.create(),
        RecordingTelemetry(),
        skip_unconfigured=False,
    )
    stream = parsing.parse_all(raws())

    assert seen == []
    assert list(stream) == []
    assert parsing.skipped == ["doc-1"]


def _run(parser: _FailingParser, telemetry: RecordingTelemetry) -> list[str]:
    _, to_skip = _parse_documents(
        raw_documents=[_raw_document()],
        parser=parser,
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
    assert telemetry.snapshot().invalidations == {REASON_PARSE_ERROR: 1}


def test_une_ValidationError_est_rejetee_sous_SA_raison() -> None:
    telemetry = RecordingTelemetry()
    error = ValidationError(REASON_FACET_ROOT_DUPLICATED, "racines en double")

    to_skip = _run(_FailingParser(error), telemetry)

    assert to_skip == ["doc-1"]
    (event,) = telemetry.events_of(DOCUMENT_INVALIDATED)
    assert event.payload["reason"] == REASON_FACET_ROOT_DUPLICATED
    assert event.payload["error"] == "racines en double"
    assert telemetry.snapshot().invalidations == {REASON_FACET_ROOT_DUPLICATED: 1}


def test_des_racines_en_double_sont_une_collision_ET_un_rejet() -> None:
    """Le document reste compté rejeté (équation de complétude) ; chaque racine en
    double est détaillée avec ses seuls fichiers."""
    telemetry = RecordingTelemetry()
    roots = {"ARTICLE": ("vigueur/a.xml", "non_vigueur/a.xml")}
    error = FacetRootCollisionError("racines en double", roots)

    _run(_FailingParser(error), telemetry)

    assert telemetry.snapshot().invalidations == {REASON_FACET_ROOT_DUPLICATED: 1}
    assert telemetry.snapshot().collisions == {COLLISION_FACET_ROOT_DUPLICATED: 1}
    (record,) = telemetry.collisions
    assert (record.identifier, record.key, record.files) == (
        "doc-1",
        "ARTICLE",
        roots["ARTICLE"],
    )


def test_le_warning_de_rejet_dit_la_raison_et_le_detail(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Sans le détail, un rejet ne se diagnostique qu'en relisant le fichier."""
    error = ValidationError(REASON_FACET_ROOT_DUPLICATED, "racines en double")

    _run(_FailingParser(error), RecordingTelemetry())

    (record,) = [r for r in caplog.records if r.levelname == "WARNING"]
    assert record.getMessage() == (
        "Document doc-1 rejeté (facet_root_duplicated) : racines en double"
    )


def test_une_exception_HORS_contrat_arrete_le_run() -> None:
    """``RoutingParser`` lève ``ValueError`` pour un document qu'il ne sait pas router :
    un bug du run, pas un document illisible."""
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
    to_process, _ = _parse_documents(
        raw_documents=[raw],
        parser=GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI),
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

    assert parsed.metadata[_UNRENAMED_KEY] == "Justice"


def test_la_duree_du_parse_est_mesuree_par_document() -> None:
    telemetry = RecordingTelemetry()

    _parse_article(skip_unconfigured=True, telemetry=telemetry)

    (duration,) = telemetry.values_of(step_measure(SourceName.LEGI, STEP_PARSE))
    assert duration >= 0


# ── Collisions de métadonnées (ADR-025) ───────────────────────────────────────


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


_LISTED = _article(
    "LEGIARTI000000000002",
    "<VERSION_A_VENIR>a</VERSION_A_VENIR><VERSION_A_VENIR>b</VERSION_A_VENIR>",
)
_REFUSED = _article("LEGIARTI000000000003", "<NUM>1</NUM><NUM>2</NUM>")


def _parse_collisions(telemetry: RecordingTelemetry) -> tuple[list[str], list[str]]:
    to_process, to_skip = _parse_documents(
        raw_documents=[_LISTED, _REFUSED],
        parser=GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI),
        telemetry=telemetry,
        skip_unconfigured=True,
    )
    return [parsed.identifier.raw for parsed in to_process], to_skip


def test_une_collision_non_configuree_est_rejetee_sous_sa_raison() -> None:
    telemetry = RecordingTelemetry()

    parsed, skipped = _parse_collisions(telemetry)

    assert parsed == ["LEGIARTI000000000002"]
    assert skipped == ["LEGIARTI000000000003"]
    invalidated = telemetry.events_of(DOCUMENT_INVALIDATED)
    assert [e.payload["reason"] for e in invalidated] == [REASON_COLLISION]
    assert telemetry.snapshot().invalidations == {REASON_COLLISION: 1}


def test_parse_ou_refuse_chaque_collision_est_comptee_au_bilan() -> None:
    """Parsé ou refusé, chaque (document, clé) en collision est compté une fois, hors
    des inconnus, et détaillé avec les fichiers d'où viennent ses valeurs."""
    telemetry = RecordingTelemetry()

    _parse_collisions(telemetry)

    stats = telemetry.snapshot()
    assert stats.collisions == {COLLISION_METADATA: 2}
    assert stats.unknowns.keys() <= {CATEGORY_TAG}
    assert {(r.identifier, r.key, r.files) for r in telemetry.collisions} == {
        ("LEGIARTI000000000002", "versions_a_venir", (_SOURCE_FILE,)),
        ("LEGIARTI000000000003", "num", (_SOURCE_FILE,)),
    }
