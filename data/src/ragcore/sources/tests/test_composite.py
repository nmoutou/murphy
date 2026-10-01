"""Le multi-source : un document routé vers la mauvaise table de rôles ne lève pas, il
devient plausible et faux. C'est ce qu'on teste d'abord.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.sources.composite import (
    CompositeConnector,
    RoutingParser,
    RoutingRelationExtractor,
)


def _raw(source: SourceName, doc_id: str) -> RawDocument:
    return RawDocument(
        source=source,
        source_document_id=doc_id,
        payload={"content": [], "files": []},
        fetched_at=datetime.now(UTC),
    )


class _FakeConnector:
    """Émet N documents estampillés de sa source, comme les vrais."""

    def __init__(
        self, source: SourceName, count: int, skipped: dict[str, int] | None = None
    ) -> None:
        self._source = source
        self._count = count
        self.skipped = skipped or {}

    async def fetch_all(self) -> AsyncIterator[RawDocument]:
        for i in range(self._count):
            yield _raw(self._source, f"{self._source.value}-{i}")


class _FakeParser:
    """Rend sa propre source, pour voir qui a parsé."""

    def __init__(self, source: SourceName) -> None:
        self.source_name = source
        self.seen: list[str] = []

    def parse(self, raw: RawDocument) -> SourceName:  # type: ignore[override]
        self.seen.append(raw.source_document_id)
        return self.source_name


# ── CompositeConnector ────────────────────────────────────────────────────────


async def test_composite_emits_every_source() -> None:
    """Les documents de toutes les sources sortent."""
    composite = CompositeConnector(
        {
            SourceName.LEGI: _FakeConnector(SourceName.LEGI, 2),
            SourceName.CASS: _FakeConnector(SourceName.CASS, 3),
        }
    )

    docs = [doc async for doc in composite.fetch_all()]

    assert len(docs) == 5
    assert [d.source for d in docs].count(SourceName.LEGI) == 2
    assert [d.source for d in docs].count(SourceName.CASS) == 3


async def test_composite_preserves_source_stamp() -> None:
    """Chaque document garde la source de son connecteur : l'invariant du routage."""
    composite = CompositeConnector(
        {
            SourceName.JADE: _FakeConnector(SourceName.JADE, 1),
            SourceName.CONSTIT: _FakeConnector(SourceName.CONSTIT, 1),
        }
    )

    by_id = {
        d.source_document_id: d.source
        for d in [doc async for doc in composite.fetch_all()]
    }

    assert by_id["jade-0"] is SourceName.JADE
    assert by_id["constit-0"] is SourceName.CONSTIT


async def test_composite_merges_skipped_counters() -> None:
    """Deux illisibles dans deux sources font deux exclusions : les compteurs se
    somment."""
    composite = CompositeConnector(
        {
            SourceName.CASS: _FakeConnector(
                SourceName.CASS, 1, skipped={"unreadable": 2}
            ),
            SourceName.JADE: _FakeConnector(
                SourceName.JADE, 1, skipped={"unreadable": 3}
            ),
        }
    )

    _ = [doc async for doc in composite.fetch_all()]

    assert composite.skipped == {"unreadable": 5}


async def test_composite_resets_skipped_between_runs() -> None:
    """Deux itérations ne cumulent pas : le compteur est celui de cette lecture."""
    composite = CompositeConnector(
        {SourceName.CASS: _FakeConnector(SourceName.CASS, 1, skipped={"unreadable": 2})}
    )

    _ = [doc async for doc in composite.fetch_all()]
    _ = [doc async for doc in composite.fetch_all()]

    assert composite.skipped == {"unreadable": 2}


def test_composite_refuses_to_be_empty() -> None:
    """Sans source, un run n'ingérerait rien en se déclarant « ok »."""
    with pytest.raises(ValueError, match="sans aucune source"):
        CompositeConnector({})


# ── RoutingParser ─────────────────────────────────────────────────────────────


def test_router_dispatches_on_document_source() -> None:
    """Chaque document part chez le parser de sa source."""
    legi, cass = _FakeParser(SourceName.LEGI), _FakeParser(SourceName.CASS)
    router = RoutingParser({SourceName.LEGI: legi, SourceName.CASS: cass})  # type: ignore[arg-type]

    assert router.parse(_raw(SourceName.LEGI, "a")) is SourceName.LEGI
    assert router.parse(_raw(SourceName.CASS, "b")) is SourceName.CASS

    # Aucun parser n'a vu le document de l'autre
    assert legi.seen == ["a"]
    assert cass.seen == ["b"]


def test_router_raises_on_unroutable_source() -> None:
    """Une source sans parser lève, jamais de parser par défaut."""
    router = RoutingParser({SourceName.LEGI: _FakeParser(SourceName.LEGI)})  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Aucun parser pour la source 'cass'"):
        router.parse(_raw(SourceName.CASS, "x"))


def test_routers_refuse_to_be_empty() -> None:
    with pytest.raises(ValueError, match="sans parser"):
        RoutingParser({})
    with pytest.raises(ValueError, match="sans extracteur"):
        RoutingRelationExtractor({})
