"""`connect` remonte au bilan ce que le connecteur a écarté : un compteur par raison,
hors `document.fetched`, donc hors équation de complétude.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_ID_MISMATCH,
    REASON_UNREADABLE,
)
from ragcore.core.statistics_measures import (
    FACETS,
    STAGE_DISCOVERY,
    STAGE_PHASE1,
    STEP_READ,
    XML_BYTES,
    document_measure,
    step_measure,
)
from ragcore.core.telemetry_events import (
    DOCUMENT_FETCHED,
    DOCUMENT_ID_MISMATCH,
    DOCUMENT_UNREADABLE,
    DOCUMENT_VERSION_SKIPPED,
)
from ragcore.orchestration.kedro.nodes.connect import connect_node
from ragcore.orchestration.kedro.stage_clock import StageClock
from ragcore.tests.fakes.telemetry import RecordingTelemetry


class _ConnectorWithSkips:
    """Rend les documents donnés, et déclare ses écarts."""

    def __init__(
        self, skipped: dict[str, int], documents: tuple[RawDocument, ...] = ()
    ) -> None:
        self.skipped = skipped
        self._documents = documents

    def discover(self) -> dict[SourceName, SourceInventory]:
        return {SourceName.LEGI: SourceInventory(documents=len(self._documents))}

    def fetch_all(self) -> Iterator[RawDocument]:
        yield from self._documents


def _run(
    connector: _ConnectorWithSkips, stage_clock: StageClock | None = None
) -> RecordingTelemetry:
    telemetry = RecordingTelemetry()
    context = PipelineContext.create(sources=(SourceName.LEGI,))
    connect_node(
        connector=connector,  # type: ignore[arg-type]
        pipeline_context=context,
        telemetry=telemetry,
        stage_clock=stage_clock or StageClock(),
        nuke_done={},
    )
    return telemetry


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


def test_la_passe_1_et_la_lecture_sont_deux_etapes() -> None:
    stage_clock = StageClock()

    _run(_ConnectorWithSkips({}), stage_clock)

    assert set(stage_clock.durations()) == {STAGE_DISCOVERY, STAGE_PHASE1}


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
