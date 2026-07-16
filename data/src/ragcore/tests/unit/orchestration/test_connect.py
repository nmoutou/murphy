"""Le node `connect` remonte au bilan ce que le connecteur a ÉCARTÉ.

Le connecteur COMPTE ses écarts (`connector.skipped`), mais ce compte s'évaporait :
aucun code ne le lisait. Le node l'émet désormais en `document.skipped` (un par
raison, HORS `document.fetched` donc hors équation de complétude) — la seule façon
dont un fichier non-document apparaît au bilan.
"""

from collections.abc import AsyncIterator

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_UNREADABLE,
)
from ragcore.core.telemetry_events import DOCUMENT_FETCHED, DOCUMENT_SKIPPED
from ragcore.orchestration.kedro.nodes.connect import connect_node
from ragcore.tests.fakes.runtime import FakeRuntime
from ragcore.tests.fakes.telemetry import RecordingTelemetry

OWNER = OwnerId("owner-1")


class _ConnectorWithSkips:
    """Connecteur idiot : ne rend AUCUN document, mais déclare ses écarts."""

    def __init__(self, skipped: dict[str, int]) -> None:
        self.skipped = skipped

    async def fetch_all(self, owner_id: OwnerId) -> AsyncIterator[RawDocument]:
        del owner_id
        return
        yield  # pragma: no cover — fait de fetch_all un générateur vide


def _run(connector: _ConnectorWithSkips) -> RecordingTelemetry:
    telemetry = RecordingTelemetry()
    context = PipelineContext.create(owner_id=OWNER, source=SourceName.LEGI)
    connect_node(
        connector=connector,  # type: ignore[arg-type]
        pipeline_context=context,
        telemetry=telemetry,
        pipeline_runtime=FakeRuntime(worker_id=0),
        nuke_done={},
    )
    return telemetry


def test_chaque_ecart_du_connecteur_emet_un_document_skipped() -> None:
    telemetry = _run(
        _ConnectorWithSkips({REASON_EXPORT_ARTIFACT: 3, REASON_UNREADABLE: 1})
    )

    skips = telemetry.events_of(DOCUMENT_SKIPPED)
    by_reason = {e.payload["reason"]: e.payload["count"] for e in skips}
    assert by_reason == {REASON_EXPORT_ARTIFACT: 3, REASON_UNREADABLE: 1}


def test_les_ecarts_ne_gonflent_pas_le_denominateur() -> None:
    """`document.fetched` compte les documents RENDUS (ici 0), jamais les écarts :
    un fichier écarté ne doit pas entrer dans `seen`, sinon l'équation ment."""
    telemetry = _run(_ConnectorWithSkips({REASON_UNREADABLE: 5}))

    fetched = telemetry.events_of(DOCUMENT_FETCHED)
    assert len(fetched) == 1
    assert fetched[0].payload["count"] == 0


def test_un_connecteur_sans_ecart_nemet_aucun_skip() -> None:
    telemetry = _run(_ConnectorWithSkips({}))

    assert telemetry.events_of(DOCUMENT_SKIPPED) == []
