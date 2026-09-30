"""Le multi-source — ce qui doit tenir, et ce qui doit CASSER.

Ces tests portent sur la seule chose que le composite peut ruiner silencieusement :
**router un document vers la mauvaise table de rôles**. Un document parsé avec la table
d'une autre source ne lève pas — il produit un document plausible et faux. C'est
précisément le mode de défaillance que le pipeline s'interdit, donc c'est ce qu'on teste
en premier.
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
    """Connecteur de test : émet N documents estampillés de SA source, comme les vrais."""

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
    """Parser de test : rend sa propre source, pour qu'on voie QUI a parsé."""

    def __init__(self, source: SourceName) -> None:
        self.source_name = source
        self.seen: list[str] = []

    def parse(self, raw: RawDocument) -> SourceName:  # type: ignore[override]
        self.seen.append(raw.source_document_id)
        return self.source_name


# ── CompositeConnector ────────────────────────────────────────────────────────


async def test_composite_emits_every_source() -> None:
    """Les documents des N sources sortent tous — aucune source n'est avalée."""
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
    """Chaque document garde la source de SON connecteur.

    C'est l'invariant qui rend le routage possible. S'il tombe, tout le reste ment.
    """
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
    """Deux fichiers illisibles dans deux sources font DEUX exclusions, pas une.

    Un compteur écrasé au lieu d'être sommé ferait disparaître un document écarté —
    et un document qui disparaît sans être compté est exactement ce que le port
    ``skipped`` existe pour empêcher.
    """
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
    """Deux itérations ne cumulent pas : le compteur est celui de CETTE lecture."""
    composite = CompositeConnector(
        {SourceName.CASS: _FakeConnector(SourceName.CASS, 1, skipped={"unreadable": 2})}
    )

    _ = [doc async for doc in composite.fetch_all()]
    _ = [doc async for doc in composite.fetch_all()]

    assert composite.skipped == {"unreadable": 2}


def test_composite_refuses_to_be_empty() -> None:
    """Un composite sans source ingérerait zéro document en se déclarant « ok »."""
    with pytest.raises(ValueError, match="sans aucune source"):
        CompositeConnector({})


# ── RoutingParser ─────────────────────────────────────────────────────────────


def test_router_dispatches_on_document_source() -> None:
    """LE test. Chaque document part chez le parser de SA source."""
    legi, cass = _FakeParser(SourceName.LEGI), _FakeParser(SourceName.CASS)
    router = RoutingParser({SourceName.LEGI: legi, SourceName.CASS: cass})  # type: ignore[arg-type]

    assert router.parse(_raw(SourceName.LEGI, "a")) is SourceName.LEGI
    assert router.parse(_raw(SourceName.CASS, "b")) is SourceName.CASS

    # Et surtout : aucun parser n'a vu le document de l'autre.
    assert legi.seen == ["a"]
    assert cass.seen == ["b"]


def test_router_raises_on_unroutable_source() -> None:
    """Une source sans parser LÈVE — elle ne tombe pas sur un défaut.

    Router vers un défaut parserait le document avec la mauvaise table : il en sortirait
    un document plausible et silencieusement faux. Mieux vaut un run qui s'arrête.
    """
    router = RoutingParser({SourceName.LEGI: _FakeParser(SourceName.LEGI)})  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Aucun parser pour la source 'cass'"):
        router.parse(_raw(SourceName.CASS, "x"))


def test_routers_refuse_to_be_empty() -> None:
    with pytest.raises(ValueError, match="sans parser"):
        RoutingParser({})
    with pytest.raises(ValueError, match="sans extracteur"):
        RoutingRelationExtractor({})
