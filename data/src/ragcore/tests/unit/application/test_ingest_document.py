"""La saga d'UN document — ce qu'elle écrit, et ce qu'elle défait quand ça casse.

Deux propriétés que le code AFFIRME et que rien n'exécutait :

1. la phase 1 n'écrit que le NŒUD — plus une seule arête (§11) ;
2. le manifest n'est écrit qu'après succès TOTAL : un run à moitié fait ne doit
   jamais laisser croire que le document est ingéré.
"""

from datetime import UTC, datetime

import pytest

from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import Operation, SourceName
from ragcore.core.models.identifiers import ELI, OwnerId
from ragcore.core.telemetry_events import (
    DOCUMENT_PERSISTED,
    RELATION_UPSERTED,
    SAGA_COMPENSATION_COMPLETED,
)
from ragcore.tests.fakes import (
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryManifestRepository,
    InMemoryVectorRepository,
    RecordingTelemetry,
)

OWNER = OwnerId("owner-1")


def _doc() -> ParsedDocument:
    return ParsedDocument(
        identifier=ELI(raw="LEGIARTI000000000001"),
        owner_id=OWNER,
        source=SourceName.LEGI,
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
        "vector_repo": InMemoryVectorRepository(),
        "manifest_repo": InMemoryManifestRepository(),
        "telemetry": RecordingTelemetry(),
    }


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext.create(owner_id=OWNER, source=SourceName.LEGI)


async def test_phase_one_writes_the_node_and_never_an_edge(stores, context) -> None:  # noqa: ANN001
    """Le retrait qui définit le lot 2 : plus une seule arête dans cette saga."""
    use_case = IngestDocumentUseCase(**stores)

    await use_case.execute(_doc(), [], Operation.INSERT, context)

    assert stores["graph_repo"].nodes == {"eli:LEGIARTI000000000001"}
    assert stores["graph_repo"].edges == []
    assert stores["telemetry"].events_of(RELATION_UPSERTED) == []
    assert len(stores["telemetry"].events_of(DOCUMENT_PERSISTED)) == 1


async def test_the_manifest_records_a_node_not_a_full_graph(stores, context) -> None:  # noqa: ANN001
    """``neo4j:node``, pas ``neo4j`` : le manifest ne doit pas promettre les arêtes."""
    use_case = IngestDocumentUseCase(**stores)

    await use_case.execute(_doc(), [], Operation.INSERT, context)

    entry = stores["manifest_repo"].entries[0]
    assert entry.targets_written == ["mongo", "qdrant", "neo4j:node"]


async def test_a_failed_saga_leaves_no_manifest_entry(stores, context) -> None:  # noqa: ANN001
    """Un document à moitié écrit ne doit JAMAIS passer pour ingéré : sans cette
    règle, le run suivant le sauterait par idempotence — et le trou serait permanent.
    """

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("qdrant est tombé")

    stores["vector_repo"].upsert = boom
    use_case = IngestDocumentUseCase(**stores)

    with pytest.raises(RuntimeError, match="qdrant est tombé"):
        await use_case.execute(_doc(), [], Operation.INSERT, context)

    assert stores["manifest_repo"].entries == []
    assert stores["telemetry"].events_of(DOCUMENT_PERSISTED) == []


async def test_a_failed_saga_compensates_what_it_had_written(stores, context) -> None:  # noqa: ANN001
    """Mongo a été écrit avant l'échec de Qdrant : la compensation doit le défaire."""

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("qdrant est tombé")

    stores["vector_repo"].upsert = boom
    use_case = IngestDocumentUseCase(**stores)

    with pytest.raises(RuntimeError):
        await use_case.execute(_doc(), [], Operation.INSERT, context)

    assert stores["document_repo"].documents == {}
    assert len(stores["telemetry"].events_of(SAGA_COMPENSATION_COMPLETED)) == 1


async def test_the_node_survives_a_later_failure(stores, context) -> None:  # noqa: ANN001
    """Neo4j est en position terminale : rien ne peut échouer APRÈS lui, donc son
    nœud n'a jamais à être compensé — ce qui préserve les arêtes entrantes que
    d'autres documents ont écrites vers lui.
    """
    use_case = IngestDocumentUseCase(**stores)

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("manifest indisponible")

    stores["manifest_repo"].append = boom

    with pytest.raises(RuntimeError):
        await use_case.execute(_doc(), [], Operation.INSERT, context)

    # L'échec est hors saga : le nœud reste, et c'est voulu.
    assert stores["graph_repo"].nodes == {"eli:LEGIARTI000000000001"}
