"""**Seul un run `ok` publie.** C'est LA règle, et elle décide de ce que voit l'utilisateur.

Un run `degraded` a laissé un corpus incomplet. Publier son empreinte propagerait la
fuite jusqu'au serving, qui répondrait sur un corpus troué **sans aucun moyen de le
savoir** — et l'utilisateur non plus. C'est le point où l'équation de complétude cesse
d'être un outil de diagnostic pour devenir la **condition de publication**.

Le corollaire est aussi important que la règle : un run raté ne casse rien. Le pointeur
ne bouge pas, et le serving continue de servir **le dernier corpus complet**.
"""

from datetime import UTC, datetime

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.published_collection import PublishedCollection
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.telemetry_events import (
    AUDIT_WRITE_FAILED,
    DOCUMENT_FAILED,
    DOCUMENT_FETCHED,
    DOCUMENT_PERSISTED,
)
from ragcore.orchestration.kedro.hooks import TelemetryHooks


class SpyPublishedRepo:
    """Enregistre ce qui a été publié — et surtout, ce qui ne l'a PAS été."""

    def __init__(self) -> None:
        self.published: list[PublishedCollection] = []

    async def publish(self, published: PublishedCollection) -> None:
        self.published.append(published)

    async def get(self) -> PublishedCollection | None:
        return self.published[-1] if self.published else None


def _summary(stats: RunStats, status: RunStatus = RunStatus.OK) -> RunSummary:
    """Le bilan tel que ``finalize`` le produit : le statut se DÉRIVE des compteurs."""
    return RunSummary.of(
        stats,
        context_run_id=RunId("r-1"),
        owner_id=OwnerId("owner-1"),
        source=SourceName.LEGI,
        started_at=datetime.now(UTC),
        status=status,
    )


def _hooks(repo: SpyPublishedRepo) -> TelemetryHooks:
    hooks = TelemetryHooks()
    hooks._published_repo = repo  # type: ignore[assignment]  # noqa: SLF001
    hooks._qdrant_collection = "9424808d"  # noqa: SLF001
    return hooks


_COMPLETE = RunStats(counts={DOCUMENT_FETCHED: 1121, DOCUMENT_PERSISTED: 1121})


def test_a_complete_run_publishes_its_fingerprint() -> None:
    repo = SpyPublishedRepo()

    _hooks(repo)._publish_collection(_summary(_COMPLETE))  # noqa: SLF001

    assert len(repo.published) == 1
    assert repo.published[0].collection_name == "9424808d"
    assert repo.published[0].document_count == 1121
    assert repo.published[0].run_id == "r-1"


def test_a_run_that_LOST_documents_does_NOT_publish() -> None:
    """98 documents perdus (le cas réel de `chunk_size: 1024`). Le corpus est troué."""
    stats = RunStats(
        counts={
            DOCUMENT_FETCHED: 1121,
            DOCUMENT_PERSISTED: 1023,
            DOCUMENT_FAILED: 98,
        }
    )
    repo = SpyPublishedRepo()

    summary = _summary(stats)
    assert summary.status is RunStatus.DEGRADED  # le bilan l'a bien vu

    _hooks(repo)._publish_collection(summary)  # noqa: SLF001

    assert repo.published == []


def test_a_run_whose_AUDIT_leaked_does_NOT_publish() -> None:
    """L'équation de complétude tombe juste — et ça ne suffit pas.

    Si l'audit a perdu des écritures, les compteurs qui *disent* que le corpus est
    complet sont eux-mêmes suspects. On ne publie pas sur une preuve qu'on ne peut plus
    croire. C'est exactement ce que la non-fuite télémétrique a rendu détectable.
    """
    stats = RunStats(
        counts={
            DOCUMENT_FETCHED: 1121,
            DOCUMENT_PERSISTED: 1121,  # l'équation tombe juste…
            AUDIT_WRITE_FAILED: 1,  # …mais sur des compteurs incomplets
        }
    )
    repo = SpyPublishedRepo()

    _hooks(repo)._publish_collection(_summary(stats))  # noqa: SLF001

    assert repo.published == []


def test_a_FAILED_run_does_not_publish() -> None:
    """Le pipeline a levé : rien ne garantit l'état des stores."""
    repo = SpyPublishedRepo()

    _hooks(repo)._publish_collection(_summary(_COMPLETE, status=RunStatus.FAILED))  # noqa: SLF001

    assert repo.published == []


def test_publishing_is_a_noop_when_the_hook_was_never_wired() -> None:
    """Un run qui n'a pas atteint `before_pipeline_run` ne doit pas exploser ici."""
    TelemetryHooks()._publish_collection(_summary(_COMPLETE))  # noqa: SLF001
