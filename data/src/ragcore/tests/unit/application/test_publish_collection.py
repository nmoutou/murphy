"""**Seul un run `ok` publie.** C'est LA règle, et elle décide de ce que voit l'utilisateur.

Un run `degraded` a laissé un corpus incomplet. Publier son empreinte propagerait la
fuite jusqu'au serving, qui répondrait sur un corpus troué **sans aucun moyen de le
savoir** — et l'utilisateur non plus. C'est le point où l'équation de complétude cesse
d'être un outil de diagnostic pour devenir la **condition de publication**.

Le corollaire est aussi important que la règle : un run raté ne casse rien. Le pointeur
ne bouge pas, et le serving continue de servir **le dernier corpus complet**.
"""

import asyncio
from datetime import UTC, datetime

from ragcore.application.publish_collection import CollectionPublisher
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.published_collection import (
    SERVING_CONTRACT_VERSION,
    PublishedCollection,
)
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.telemetry_events import (
    AUDIT_WRITE_FAILED,
    DOCUMENT_FAILED,
    DOCUMENT_FETCHED,
    DOCUMENT_PERSISTED,
)


class SpyPublishedRepo:
    """Enregistre ce qui a été publié — et surtout, ce qui ne l'a PAS été."""

    def __init__(self, current: PublishedCollection | None = None) -> None:
        self.published: list[PublishedCollection] = [current] if current else []

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


def _publish(
    repo: SpyPublishedRepo, summary: RunSummary, *, is_full_run: bool = True
) -> PublishedCollection | None:
    publisher = CollectionPublisher(repo, "9424808d", is_full_run=is_full_run)
    return asyncio.run(publisher.publish_if_complete(summary))


def _pointer(version: int | None) -> PublishedCollection:
    """Le pointeur en place avant ce run, à une version donnée du contrat."""
    return PublishedCollection(
        collection_name="9424808d",
        fingerprint="9424808d",
        run_id=RunId("r-0"),
        document_count=769,
        serving_contract_version=version,
    )


_COMPLETE = RunStats(counts={DOCUMENT_FETCHED: 1121, DOCUMENT_PERSISTED: 1121})


def test_a_complete_run_publishes_its_fingerprint() -> None:
    repo = SpyPublishedRepo()

    _publish(repo, _summary(_COMPLETE))

    assert len(repo.published) == 1
    assert repo.published[0].collection_name == "9424808d"
    assert repo.published[0].document_count == 1121
    assert repo.published[0].run_id == "r-1"
    assert repo.published[0].serving_contract_version == SERVING_CONTRACT_VERSION


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

    _publish(repo, summary)

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

    _publish(repo, _summary(stats))

    assert repo.published == []


def test_a_FAILED_run_does_not_publish() -> None:
    """Le pipeline a levé : rien ne garantit l'état des stores."""
    repo = SpyPublishedRepo()

    _publish(repo, _summary(_COMPLETE, status=RunStatus.FAILED))

    assert repo.published == []


def test_a_publication_returns_the_pointer_and_a_refusal_returns_None() -> None:
    """Le hook n'a pas à relire le dépôt pour savoir ce qui est parti au serving."""
    published = _publish(SpyPublishedRepo(), _summary(_COMPLETE))
    refused = _publish(SpyPublishedRepo(), _summary(_COMPLETE, status=RunStatus.FAILED))

    assert published is not None and published.collection_name == "9424808d"
    assert refused is None


# --- ADR-039 §3 : un run restreint n'introduit jamais une version du contrat ---------


def test_a_restricted_run_publishes_over_a_pointer_of_the_SAME_version() -> None:
    repo = SpyPublishedRepo(_pointer(SERVING_CONTRACT_VERSION))

    _publish(repo, _summary(_COMPLETE), is_full_run=False)

    assert len(repo.published) == 2
    assert repo.published[-1].run_id == "r-1"


def test_a_restricted_run_does_NOT_publish_over_a_pointer_without_version() -> None:
    """Il n'a réécrit que ses sources : la collection mêle encore l'ancien format."""
    repo = SpyPublishedRepo(_pointer(None))

    _publish(repo, _summary(_COMPLETE), is_full_run=False)

    assert [p.run_id for p in repo.published] == ["r-0"]


def test_a_restricted_run_does_NOT_publish_when_no_pointer_exists() -> None:
    repo = SpyPublishedRepo()

    _publish(repo, _summary(_COMPLETE), is_full_run=False)

    assert repo.published == []


def test_a_restricted_run_does_NOT_publish_over_ANOTHER_version() -> None:
    repo = SpyPublishedRepo(_pointer(SERVING_CONTRACT_VERSION - 1))

    _publish(repo, _summary(_COMPLETE), is_full_run=False)

    assert [p.run_id for p in repo.published] == ["r-0"]


def test_a_full_run_publishes_over_a_pointer_without_version() -> None:
    """C'est le chemin d'un bump : le run complet réécrit tout, puis publie."""
    repo = SpyPublishedRepo(_pointer(None))

    _publish(repo, _summary(_COMPLETE))

    assert repo.published[-1].serving_contract_version == SERVING_CONTRACT_VERSION
