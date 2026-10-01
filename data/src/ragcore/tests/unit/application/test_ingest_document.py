"""La saga d'UN document — ce qu'elle écrit, et ce qu'elle défait quand ça casse.

Deux propriétés que le code AFFIRME et que rien n'exécutait :

1. la phase 1 n'écrit que le NŒUD — plus une seule arête (§11) ;
2. ``document.persisted`` n'est émis qu'après succès TOTAL : un run à moitié fait ne
   doit jamais laisser croire que le document est ingéré.
"""

from datetime import UTC, datetime

import pytest

from ragcore.application.ingest_document import IngestDocumentUseCase, IngestionStores
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.telemetry_events import (
    DOCUMENT_PERSISTED,
    RELATION_UPSERTED,
    SAGA_COMPENSATION_COMPLETED,
    SAGA_COMPENSATION_FAILED,
)
from ragcore.tests.fakes import (
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryVectorRepository,
    RecordingTelemetry,
)


def _doc() -> ParsedDocument:
    return ParsedDocument(
        identifier=Identifier(raw="LEGIARTI000000000001"),
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
        "telemetry": RecordingTelemetry(),
    }


def _use_case(stores: dict) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(
        IngestionStores(
            documents=stores["document_repo"],
            graph=stores["graph_repo"],
            vectors=stores["vector_repo"],
        ),
        stores["telemetry"],
    )


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext.create(source=SourceName.LEGI)


async def test_phase_one_writes_the_node_and_never_an_edge(stores, context) -> None:  # noqa: ANN001
    """Le retrait qui définit le lot 2 : plus une seule arête dans cette saga."""
    use_case = _use_case(stores)

    await use_case.execute(_doc(), [], context)

    assert stores["graph_repo"].nodes == {"LEGIARTI000000000001"}
    assert stores["graph_repo"].edges == []
    assert stores["telemetry"].events_of(RELATION_UPSERTED) == []
    assert len(stores["telemetry"].events_of(DOCUMENT_PERSISTED)) == 1


async def test_a_failed_saga_is_not_counted_persisted(stores, context) -> None:  # noqa: ANN001
    """Un document à moitié écrit ne doit JAMAIS passer pour ingéré : le bilan
    annoncerait un corpus complet sur un run qui a perdu un document.
    """

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("qdrant est tombé")

    stores["vector_repo"].upsert = boom
    use_case = _use_case(stores)

    with pytest.raises(RuntimeError, match="qdrant est tombé"):
        await use_case.execute(_doc(), [], context)

    assert stores["telemetry"].events_of(DOCUMENT_PERSISTED) == []


async def test_a_failed_saga_compensates_what_it_had_written(stores, context) -> None:  # noqa: ANN001
    """Mongo a été écrit avant l'échec de Qdrant : la compensation doit le défaire."""

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("qdrant est tombé")

    stores["vector_repo"].upsert = boom
    use_case = _use_case(stores)

    with pytest.raises(RuntimeError):
        await use_case.execute(_doc(), [], context)

    assert stores["document_repo"].documents == {}
    assert len(stores["telemetry"].events_of(SAGA_COMPENSATION_COMPLETED)) == 1


async def test_a_failed_compensation_is_counted_and_told_truthfully(
    stores, context
) -> None:  # noqa: ANN001
    """Le forward de Qdrant casse ⇒ compensation ; MAIS le rollback de Mongo casse
    aussi. L'écrit partiel qui subsiste doit être COMPTÉ (SAGA_COMPENSATION_FAILED,
    avec son `step`) et l'audit ne doit PAS prétendre à un rollback propre.
    """

    async def boom(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("qdrant est tombé")

    async def boom_rollback(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("mongo refuse de se défaire")

    stores["vector_repo"].upsert = boom  # déclenche la compensation
    stores["document_repo"].delete = boom_rollback  # …dont le rollback rate
    use_case = _use_case(stores)

    with pytest.raises(RuntimeError, match="qdrant est tombé"):
        await use_case.execute(_doc(), [], context)

    # La compensation ratée est comptée, ventilée par le store fautif.
    failed = stores["telemetry"].events_of(SAGA_COMPENSATION_FAILED)
    assert len(failed) == 1
    assert failed[0].payload["step"] == "mongo_upsert"
    assert failed[0].success is False

    # …et le bilan de compensation dit la vérité : rollback NON propre.
    completed = stores["telemetry"].events_of(SAGA_COMPENSATION_COMPLETED)
    assert len(completed) == 1
    assert completed[0].success is False
    assert completed[0].payload["failed_compensations"] == ["mongo_upsert"]


async def test_a_rewrite_replaces_in_place_without_a_preceding_delete(
    stores, context
) -> None:  # noqa: ANN001
    """F16 — le trou fermé : une réécriture ne pré-supprime plus l'ancienne version.

    Avant, le forward Mongo faisait ``delete`` PUIS ``insert`` — une fenêtre où
    l'identifiant n'existait plus, et un rollback qui la rendait durable. Le forward est
    maintenant un ``upsert`` atomique (``replace_one``). L'observable : sur une
    réécriture RÉUSSIE, aucun ``delete`` n'a été poussé sur le document (la liste ``deleted`` du fake
    ne se remplit que par une compensation, qui n'a pas lieu ici). Le document neuf est
    en place, seul sous son identifiant.
    """
    use_case = _use_case(stores)

    await use_case.execute(_doc(), [], context)
    await use_case.execute(_doc(), [], context)

    assert stores["document_repo"].deleted == []
    assert list(stores["document_repo"].documents) == ["LEGIARTI000000000001"]
    assert len(stores["telemetry"].events_of(DOCUMENT_PERSISTED)) == 2
