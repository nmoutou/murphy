"""Le node `connect` remonte au bilan ce que le connecteur a ÉCARTÉ.

Le connecteur COMPTE ses écarts (`connector.skipped`), mais ce compte s'évaporait :
aucun code ne le lisait. Le node l'émet désormais en un compteur par raison
(`document.version_skipped`, `document.unreadable`), HORS `document.fetched` donc hors
équation de complétude — la seule façon dont un fichier non-document apparaît au bilan.
"""

from collections.abc import AsyncIterator

import pytest

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_UNREADABLE,
)
from ragcore.core.telemetry_events import (
    DOCUMENT_FETCHED,
    DOCUMENT_UNREADABLE,
    DOCUMENT_VERSION_SKIPPED,
)
from ragcore.orchestration.kedro.nodes.connect import connect_node
from ragcore.tests.fakes.runtime import FakeRuntime
from ragcore.tests.fakes.telemetry import RecordingTelemetry


class _ConnectorWithSkips:
    """Connecteur idiot : ne rend AUCUN document, mais déclare ses écarts."""

    def __init__(self, skipped: dict[str, int]) -> None:
        self.skipped = skipped

    async def fetch_all(self) -> AsyncIterator[RawDocument]:
        return
        yield  # pragma: no cover — fait de fetch_all un générateur vide


def _run(connector: _ConnectorWithSkips) -> RecordingTelemetry:
    telemetry = RecordingTelemetry()
    context = PipelineContext.create(sources=(SourceName.LEGI,))
    connect_node(
        connector=connector,  # type: ignore[arg-type]
        pipeline_context=context,
        telemetry=telemetry,
        pipeline_runtime=FakeRuntime(worker_id=0),
        nuke_done={},
    )
    return telemetry


def test_chaque_raison_d_ecart_emet_son_propre_compteur() -> None:
    telemetry = _run(
        _ConnectorWithSkips({REASON_EXPORT_ARTIFACT: 3, REASON_UNREADABLE: 1})
    )

    versions = telemetry.events_of(DOCUMENT_VERSION_SKIPPED)
    unreadable = telemetry.events_of(DOCUMENT_UNREADABLE)
    assert [e.payload["count"] for e in versions] == [3]
    assert [e.payload["count"] for e in unreadable] == [1]


def test_une_raison_inconnue_leve() -> None:
    """Un écart qu'on ne sait pas nommer ne se range pas dans un fourre-tout."""
    with pytest.raises(KeyError):
        _run(_ConnectorWithSkips({"raison_inventee": 2}))


def test_les_ecarts_ne_gonflent_pas_le_denominateur() -> None:
    """`document.fetched` compte les documents RENDUS (ici 0), jamais les écarts :
    un fichier écarté ne doit pas entrer dans `seen`, sinon l'équation ment."""
    telemetry = _run(_ConnectorWithSkips({REASON_UNREADABLE: 5}))

    fetched = telemetry.events_of(DOCUMENT_FETCHED)
    assert len(fetched) == 1
    assert fetched[0].payload["count"] == 0


def test_un_connecteur_sans_ecart_nemet_aucun_skip() -> None:
    telemetry = _run(_ConnectorWithSkips({}))

    assert telemetry.events_of(DOCUMENT_VERSION_SKIPPED) == []
    assert telemetry.events_of(DOCUMENT_UNREADABLE) == []
