"""La saga d'un document : la phase 1 n'écrit que le nœud, et ``document.persisted``
n'est émis qu'après succès total.
"""

from datetime import UTC, datetime

import pytest

from ragcore.application.ingest_document import (
    DocumentRelations,
    IngestDocumentUseCase,
    IngestionStores,
)
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.relation import Relation
from ragcore.core.models.search_content import SearchContent
from ragcore.core.models.unformatted_relation import UnformattedRelation
from ragcore.core.statistics_measures import STEP_MONGO, STEP_NEO4J, STEP_OPENSEARCH
from ragcore.core.telemetry_events import (
    DOCUMENT_PERSISTED,
    RELATION_UPSERTED,
    SAGA_COMPENSATION_COMPLETED,
    SAGA_COMPENSATION_FAILED,
)
from ragcore.tests.fakes import (
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryPendingRepository,
    InMemorySearchIndex,
    InMemoryTransitRepository,
    InMemoryUnformattedRepository,
    RecordingTelemetry,
)


def _doc() -> ParsedDocument:
    return ParsedDocument(
        identifier=Identifier(raw="LEGIARTI000000000001"),
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title="Article 1",
        content="contenu",
        structure={},
        metadata={},
        parsed_at=datetime.now(UTC),
    )


@pytest.fixture
def stores() -> dict:
    return {
        "document_repo": InMemoryDocumentRepository(),
        "graph_repo": InMemoryGraphRepository(),
        "search_index": InMemorySearchIndex(),
        "unformatted_repo": InMemoryUnformattedRepository(),
        "transit_repo": InMemoryTransitRepository(),
        "telemetry": RecordingTelemetry(),
    }


def _use_case(stores: dict) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(
        IngestionStores(
            documents=stores["document_repo"],
            graph=stores["graph_repo"],
            search_index=stores["search_index"],
            pending=InMemoryPendingRepository(),
            unformatted=stores["unformatted_repo"],
            transit=stores["transit_repo"],
        ),
        stores["telemetry"],
    )


def _unformatted(target_text: str) -> UnformattedRelation:
    return UnformattedRelation(
        source_identifier=Identifier(raw="LEGIARTI000000000001"),
        target_text=target_text,
        relation_type="cite",
        sens="source",
        source=SourceName.LEGI,
    )


async def _fail_opensearch(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
    raise RuntimeError("opensearch est tombé")


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext.create(sources=(SourceName.LEGI,))


async def test_phase_one_writes_the_node_and_never_an_edge(stores, context) -> None:  # noqa: ANN001
    """Aucune arête dans cette saga."""
    use_case = _use_case(stores)

    await use_case.execute(_doc(), SearchContent(), context)

    assert stores["graph_repo"].nodes == {"LEGIARTI000000000001"}
    assert stores["graph_repo"].edges == []
    assert stores["telemetry"].events_of(RELATION_UPSERTED) == []
    assert len(stores["telemetry"].events_of(DOCUMENT_PERSISTED)) == 1


async def test_the_write_durations_come_back_one_per_store(stores, context) -> None:  # noqa: ANN001
    """Les deux étapes Mongo s'additionnent sous une seule mesure."""
    durations = await _use_case(stores).execute(_doc(), SearchContent(), context)

    assert set(durations) == {STEP_MONGO, STEP_OPENSEARCH, STEP_NEO4J}
    assert all(milliseconds >= 0 for milliseconds in durations.values())


async def test_a_failed_saga_is_not_counted_persisted(stores, context) -> None:  # noqa: ANN001
    """Un document à moitié écrit n'est pas compté persisté."""

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("opensearch est tombé")

    stores["search_index"].index_document = boom
    use_case = _use_case(stores)

    with pytest.raises(RuntimeError, match="opensearch est tombé"):
        await use_case.execute(_doc(), SearchContent(), context)

    assert stores["telemetry"].events_of(DOCUMENT_PERSISTED) == []


async def test_a_failed_saga_compensates_what_it_had_written(stores, context) -> None:  # noqa: ANN001
    """Mongo, écrit avant l'échec d'OpenSearch, est défait."""

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("opensearch est tombé")

    stores["search_index"].index_document = boom
    use_case = _use_case(stores)

    with pytest.raises(RuntimeError):
        await use_case.execute(_doc(), SearchContent(), context)

    assert stores["document_repo"].documents == {}
    assert len(stores["telemetry"].events_of(SAGA_COMPENSATION_COMPLETED)) == 1


async def test_a_failed_compensation_is_counted_and_told_truthfully(
    stores, context
) -> None:  # noqa: ANN001
    """La compensation de Mongo échoue aussi : l'écrit partiel est compté, et l'audit
    ne prétend pas à un rollback propre."""

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("opensearch est tombé")

    async def boom_rollback(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("mongo refuse de se défaire")

    stores["search_index"].index_document = boom  # déclenche la compensation
    stores["document_repo"].delete = boom_rollback  # …dont le rollback rate
    use_case = _use_case(stores)

    with pytest.raises(RuntimeError, match="opensearch est tombé"):
        await use_case.execute(_doc(), SearchContent(), context)

    # La compensation ratée est comptée, avec le store fautif
    failed = stores["telemetry"].events_of(SAGA_COMPENSATION_FAILED)
    assert len(failed) == 1
    assert failed[0].payload["step"] == "mongo_upsert"
    assert failed[0].success is False

    # …et le bilan dit que le rollback n'est pas propre
    completed = stores["telemetry"].events_of(SAGA_COMPENSATION_COMPLETED)
    assert len(completed) == 1
    assert completed[0].success is False
    assert completed[0].payload["failed_compensations"] == ["mongo_upsert"]


async def test_a_rewrite_replaces_in_place_without_a_preceding_delete(
    stores, context
) -> None:  # noqa: ANN001
    """Une réécriture réussie ne supprime jamais l'ancienne version : le remplacement
    est atomique."""
    use_case = _use_case(stores)

    await use_case.execute(_doc(), SearchContent(), context)
    await use_case.execute(_doc(), SearchContent(), context)

    assert stores["document_repo"].deleted == []
    assert stores["search_index"].deleted == []
    assert list(stores["document_repo"].documents) == ["LEGIARTI000000000001"]
    assert list(stores["search_index"].documents) == ["LEGIARTI000000000001"]
    assert len(stores["telemetry"].events_of(DOCUMENT_PERSISTED)) == 2


async def test_the_unformatted_relations_are_written_with_the_run_stamps(
    stores, context
) -> None:  # noqa: ANN001
    """ADR-021 : les cibles décrites vont dans leur collection, estampillées du run."""
    use_case = _use_case(stores)
    relation = _unformatted("Articles 1103 et 1229 du code civil.")

    await use_case.execute(
        _doc(), SearchContent(), context, DocumentRelations(unformatted=[relation])
    )

    [row] = stores["unformatted_repo"].rows.values()
    assert row.relation == relation
    assert row.first_seen_run == context.run_id
    assert row.last_seen_run == context.run_id


async def test_a_failed_saga_removes_the_unformatted_relations_born_in_its_run(
    stores, context
) -> None:  # noqa: ANN001
    """OpenSearch casse : les relations non formatées nées dans ce run sont défaites."""
    stores["search_index"].index_document = _fail_opensearch
    use_case = _use_case(stores)

    with pytest.raises(RuntimeError, match="opensearch est tombé"):
        await use_case.execute(
            _doc(),
            SearchContent(),
            context,
            DocumentRelations(unformatted=[_unformatted("code civil")]),
        )

    assert stores["unformatted_repo"].rows == {}


async def test_a_failed_saga_keeps_the_unformatted_relations_of_earlier_runs(
    stores, context
) -> None:  # noqa: ANN001
    """Une relation vue par un run précédent survit à la compensation."""
    known = _unformatted("code civil")
    await _use_case(stores).execute(
        _doc(), SearchContent(), context, DocumentRelations(unformatted=[known])
    )

    stores["search_index"].index_document = _fail_opensearch
    next_run = PipelineContext.create(sources=(SourceName.LEGI,))
    with pytest.raises(RuntimeError, match="opensearch est tombé"):
        await _use_case(stores).execute(
            _doc(),
            SearchContent(),
            next_run,
            DocumentRelations(unformatted=[known, _unformatted("code pénal")]),
        )

    [row] = stores["unformatted_repo"].rows.values()
    assert row.relation == known, "seule la relation née dans ce run est défaite"
    assert row.first_seen_run == context.run_id


def _relation(target: str) -> Relation:
    return Relation(
        source_identifier=Identifier(raw="LEGIARTI000000000001"),
        target_identifier=Identifier(raw=target),
        relation_type="cite",
        source=SourceName.LEGI,
    )


async def test_the_relations_wait_in_transit_with_the_run_stamp(
    stores, context
) -> None:  # noqa: ANN001
    """ADR-034 §4 : une ligne par relation, jamais une arête en phase 1."""
    relations = [_relation("LEGIARTI000000000002"), _relation("LEGIARTI000000000003")]

    await _use_case(stores).execute(
        _doc(), SearchContent(), context, DocumentRelations(relations=relations)
    )

    assert stores["transit_repo"].rows == [(r, context.run_id) for r in relations]
    assert stores["graph_repo"].edges == []


async def test_a_failed_saga_removes_its_relations_in_transit_for_this_run_only(
    stores, context
) -> None:  # noqa: ANN001
    """Les lignes d'un autre run, ou d'un autre document, survivent."""
    other_run = PipelineContext.create(sources=(SourceName.LEGI,))
    kept = _relation("LEGIARTI000000000009")
    await stores["transit_repo"].insert_many([kept], other_run.run_id)
    stores["search_index"].index_document = _fail_opensearch

    with pytest.raises(RuntimeError, match="opensearch est tombé"):
        await _use_case(stores).execute(
            _doc(),
            SearchContent(),
            context,
            DocumentRelations(relations=[_relation("LEGIARTI000000000002")]),
        )

    assert stores["transit_repo"].rows == [(kept, other_run.run_id)]
