"""La lecture remonte au bilan ce que le connecteur a écarté : un compteur par raison,
hors `document.fetched`, donc hors équation de complétude.
"""

import logging
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ragcore.application.run_context import PipelineContext
from ragcore.application.source_reading import SourceReading
from ragcore.core.models.collision_record import CollisionRecord
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.models.problems import CopyStamp, FileProblem, SupersededCopy
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_ID_MISMATCH,
    REASON_SUPERSEDED,
    REASON_UNREADABLE,
)
from ragcore.core.statistics_measures import (
    FACETS,
    STEP_READ,
    XML_BYTES,
    document_measure,
    step_measure,
)
from ragcore.core.telemetry_events import (
    DOCUMENT_FETCHED,
    DOCUMENT_ID_MISMATCH,
    DOCUMENT_SUPERSEDED,
    DOCUMENT_UNREADABLE,
    DOCUMENT_VERSION_SKIPPED,
)
from ragcore.tests.fakes.telemetry import RecordingTelemetry


class _ConnectorWithSkips:
    """Rend les documents donnés, et déclare ses écarts."""

    def __init__(
        self, skipped: dict[str, int], documents: tuple[RawDocument, ...] = ()
    ) -> None:
        self.skipped = skipped
        self.collisions: list[CollisionRecord] = []
        self.problems: list[FileProblem] = []
        self._documents = documents
        self.yielded: list[RawDocument] = []

    def discover(self) -> dict[SourceName, SourceInventory]:
        count = len(self._documents)
        return {SourceName.LEGI: SourceInventory(total=count * 2, retained=count)}

    def fetch_all(self) -> Iterator[RawDocument]:
        for document in self._documents:
            self.yielded.append(document)
            yield document


def _run(
    connector: _ConnectorWithSkips, sink: "_SpySink | None" = None
) -> RecordingTelemetry:
    telemetry = RecordingTelemetry()
    context = PipelineContext.create(sources=(SourceName.LEGI,))
    reading = SourceReading(connector, context, telemetry)  # type: ignore[arg-type]
    reading.discover(sink or _SpySink())
    list(reading.documents())
    reading.declare_counts()
    return telemetry


class _SpySink:
    def __init__(self) -> None:
        self.inventories: dict[SourceName, SourceInventory] = {}

    def record_inventories(
        self, inventories: Mapping[SourceName, SourceInventory]
    ) -> None:
        self.inventories.update(inventories)


def test_l_inventaire_rejoint_le_bilan_et_un_run_partiel_est_annonce(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sink = _SpySink()

    with caplog.at_level(logging.WARNING):
        _run(_ConnectorWithSkips({}, (_raw([]),)), sink=sink)

    assert sink.inventories == {SourceName.LEGI: SourceInventory(total=2, retained=1)}
    assert "1 documents retenus sur 2" in caplog.text


def _raw(files: list[Path]) -> RawDocument:
    return RawDocument(
        source=SourceName.LEGI,
        source_document_id="LEGIARTI000000000001",
        payload={"content": [], "files": [str(file) for file in files]},
        fetched_at=datetime.now(UTC),
    )


def test_la_taille_et_les_facettes_de_chaque_document_sont_mesurees(
    tmp_path: Path,
) -> None:
    facets = [tmp_path / "a.xml", tmp_path / "b.xml"]
    facets[0].write_bytes(b"x" * 10)
    facets[1].write_bytes(b"x" * 5)

    telemetry = _run(_ConnectorWithSkips({}, (_raw(facets),)))

    assert telemetry.values_of(document_measure(SourceName.LEGI, XML_BYTES)) == [15]
    assert telemetry.values_of(document_measure(SourceName.LEGI, FACETS)) == [2]
    assert len(telemetry.values_of(step_measure(SourceName.LEGI, STEP_READ))) == 1


def test_la_passe_1_rend_le_nombre_de_documents_retenus() -> None:
    connector = _ConnectorWithSkips({}, (_raw([]), _raw([])))
    reading = SourceReading(
        connector,  # type: ignore[arg-type]
        PipelineContext.create(sources=(SourceName.LEGI,)),
        RecordingTelemetry(),
    )

    assert reading.discover(_SpySink()) == 2


def test_la_lecture_est_un_flux() -> None:
    """Rien n'est lu d'avance : un document à la fois."""
    connector = _ConnectorWithSkips({}, (_raw([]), _raw([])))
    reading = SourceReading(
        connector,  # type: ignore[arg-type]
        PipelineContext.create(sources=(SourceName.LEGI,)),
        RecordingTelemetry(),
    )
    reading.discover(_SpySink())

    stream = reading.documents()
    next(stream)

    assert len(connector.yielded) == 1


def test_un_ID_qui_n_est_pas_le_nom_a_son_compteur() -> None:
    telemetry = _run(_ConnectorWithSkips({REASON_ID_MISMATCH: 4}))

    (event,) = telemetry.events_of(DOCUMENT_ID_MISMATCH)
    assert event.payload["count"] == 4


def test_chaque_raison_d_ecart_emet_son_propre_compteur() -> None:
    telemetry = _run(
        _ConnectorWithSkips({REASON_EXPORT_ARTIFACT: 3, REASON_UNREADABLE: 1})
    )

    versions = telemetry.events_of(DOCUMENT_VERSION_SKIPPED)
    unreadable = telemetry.events_of(DOCUMENT_UNREADABLE)
    assert [e.payload["count"] for e in versions] == [3]
    assert [e.payload["count"] for e in unreadable] == [1]


def test_une_raison_inconnue_leve() -> None:
    """Un écart qu'on ne sait pas nommer lève, plutôt que de finir dans un fourre-tout."""
    with pytest.raises(KeyError):
        _run(_ConnectorWithSkips({"raison_inventee": 2}))


def test_les_ecarts_ne_gonflent_pas_le_denominateur() -> None:
    """`document.fetched` compte les documents rendus, jamais les écarts."""
    telemetry = _run(_ConnectorWithSkips({REASON_UNREADABLE: 5}))

    fetched = telemetry.events_of(DOCUMENT_FETCHED)
    assert len(fetched) == 1
    assert fetched[0].payload["count"] == 0


def test_un_connecteur_sans_ecart_nemet_aucun_skip() -> None:
    telemetry = _run(_ConnectorWithSkips({}))

    assert telemetry.events_of(DOCUMENT_VERSION_SKIPPED) == []
    assert telemetry.events_of(DOCUMENT_UNREADABLE) == []


def test_les_collisions_du_connecteur_sont_declarees() -> None:
    """Leur document est émis : ni compteur d'écart, ni effet sur le dénominateur."""
    connector = _ConnectorWithSkips({})
    record = CollisionRecord(
        source=SourceName.LEGI,
        reason="duplicate_copy",
        identifier="LEGIARTI1",
        key="ARTICLE",
        files=("non_vigueur/LEGIARTI1.xml", "en_vigueur/LEGIARTI1.xml"),
    )
    connector.collisions = [record]

    telemetry = _run(connector)

    assert telemetry.collisions == [record]
    assert telemetry.snapshot().collisions == {"duplicate_copy": 1}
    assert [event.event_type for event in telemetry.events] == [DOCUMENT_FETCHED]


def test_une_copie_ecartee_est_comptee_et_detaillee_hors_collisions() -> None:
    connector = _ConnectorWithSkips({REASON_SUPERSEDED: 1})
    copy = SupersededCopy(
        source=SourceName.LEGI,
        identifier="LEGIARTI1",
        root="ARTICLE",
        kept=CopyStamp(path="non_vigueur/LEGIARTI1.xml", mtime_ns=2_000),
        discarded=CopyStamp(path="en_vigueur/LEGIARTI1.xml", mtime_ns=1_000),
    )
    connector.problems = [copy]

    telemetry = _run(connector)

    assert telemetry.problems == [copy]
    assert telemetry.snapshot().collisions == {}
    (event,) = telemetry.events_of(DOCUMENT_SUPERSEDED)
    assert event.payload == {"count": 1}
