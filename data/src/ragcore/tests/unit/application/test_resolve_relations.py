"""La phase 2 — le comptage exact (§12) et le cache des pendantes (§13).

Le défaut que ces tests interdisent de revenir : ``RELATION_UPSERTED`` émettait
``count=len(relations)`` — le nombre d'arêtes *tentées*. Une arête dont le
``MATCH (b)`` ne trouvait rien n'était pas écrite, ne levait rien, et n'émettait
rien. Elle disparaissait, et le compteur affirmait le contraire.

Ici, l'invariant est exécuté : ``written + pending == entrée``. Rien ne s'évapore.
"""

from datetime import UTC, datetime

import pytest

from ragcore.application.resolve_relations import ResolveRelationsService
from ragcore.application.run_context import PipelineContext
from ragcore.core.links import CITES
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.pending import PendingRelation
from ragcore.core.models.relation import Relation
from ragcore.core.telemetry_events import (
    RELATION_PENDING,
    RELATION_PROMOTED,
    RELATION_UPSERTED,
)
from ragcore.tests.fakes import (
    InMemoryGraphRepository,
    InMemoryPendingRepository,
    RecordingTelemetry,
)

A, B, MISSING = "000000000001", "000000000002", "000000000404"


def _identifier(suffix: str) -> Identifier:
    return Identifier(raw=f"LEGIARTI{suffix}")


def _doc(suffix: str) -> ParsedDocument:
    return ParsedDocument(
        identifier=_identifier(suffix),
        source=SourceName.LEGI,
        title="t",
        content="c",
        structure={},
        metadata={},
        parsed_at=datetime.now(UTC),
    )


def _rel(source: str, target: str) -> Relation:
    return Relation(
        source_identifier=_identifier(source),
        target_identifier=_identifier(target),
        relation_type=CITES,
        source=SourceName.LEGI,
    )


@pytest.fixture
def graph() -> InMemoryGraphRepository:
    return InMemoryGraphRepository()


@pytest.fixture
def pending() -> InMemoryPendingRepository:
    return InMemoryPendingRepository()


@pytest.fixture
def telemetry() -> RecordingTelemetry:
    return RecordingTelemetry()


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext.create(sources=(SourceName.LEGI,))


@pytest.fixture
def service(graph, pending, telemetry) -> ResolveRelationsService:  # noqa: ANN001
    return ResolveRelationsService(graph, pending, telemetry)


async def test_a_resolvable_edge_is_written_and_counted(
    service, graph, telemetry, context
) -> None:  # noqa: ANN001
    await graph.merge_document_node(_doc(A))
    await graph.merge_document_node(_doc(B))

    outcome = await service.execute([_rel(A, B)], {f"LEGIARTI{A}"}, context)

    assert outcome.written_count == 1
    assert outcome.pending_count == 0
    events = telemetry.events_of(RELATION_UPSERTED)
    assert len(events) == 1
    assert events[0].payload["count"] == 1  # les arêtes ÉCRITES, pas tentées


async def test_an_unresolvable_edge_becomes_a_pending_not_a_silence(
    graph, pending, telemetry, context
) -> None:  # noqa: ANN001
    """Le cœur du §12 : la cible n'existe pas, donc rien n'est écrit — et on le DIT."""
    service = ResolveRelationsService(graph, pending, telemetry)
    await graph.merge_document_node(_doc(A))  # la cible MISSING n'est pas là

    outcome = await service.execute([_rel(A, MISSING)], set(), context)

    assert outcome.written_count == 0
    assert outcome.pending_count == 1
    assert graph.edges == []  # rien d'écrit dans le graphe
    assert len(pending.pendings) == 1  # mais la relation existe toujours quelque part
    assert len(telemetry.events_of(RELATION_PENDING)) == 1
    assert telemetry.events_of(RELATION_UPSERTED) == []  # aucun comptage mensonger


async def test_nothing_is_lost_between_input_and_output(
    service, graph, context
) -> None:  # noqa: ANN001
    """L'invariant du port : written + pending == entrée. Toujours."""
    await graph.merge_document_node(_doc(A))
    await graph.merge_document_node(_doc(B))
    relations = [_rel(A, B), _rel(A, MISSING), _rel(B, MISSING)]

    outcome = await service.execute(relations, set(), context)

    assert outcome.written_count + outcome.pending_count == len(relations)


async def test_a_pending_is_promoted_when_its_target_finally_arrives(
    graph, pending, telemetry, context
) -> None:  # noqa: ANN001
    """Le §13 : le corpus s'enrichit, le trou se referme — sans rejouer tout le backlog."""
    service = ResolveRelationsService(graph, pending, telemetry)
    await graph.merge_document_node(_doc(A))
    await service.execute([_rel(A, B)], set(), context)  # B n'existe pas encore
    assert len(pending.pendings) == 1

    # Run suivant : B arrive.
    await graph.merge_document_node(_doc(B))
    outcome = await service.execute([], {f"LEGIARTI{B}"}, context)

    assert outcome.promoted_count == 1
    assert pending.pendings == {}  # la pendante résolue quitte le cache
    assert len(graph.edges) == 1  # l'arête est enfin dans le graphe
    assert len(telemetry.events_of(RELATION_PROMOTED)) == 1


async def test_replay_is_bounded_by_the_delta_not_the_backlog(
    service, graph, pending, context
) -> None:  # noqa: ANN001
    """Une pendante qui dort depuis 200 runs ne coûte rien : on ne la retente pas.

    C'est ce qui rend le rejeu tenable à l'échelle du corpus — le coût suit le
    nombre de nœuds ÉCRITS par ce run, jamais la taille du cache.
    """
    await pending.upsert_many(
        [PendingRelation.from_relation(_rel(A, MISSING), context.run_id)]
    )
    await graph.merge_document_node(_doc(B))

    outcome = await service.execute([], {f"LEGIARTI{B}"}, context)

    assert outcome.promoted_count == 0
    assert len(pending.pendings) == 1  # la vieille pendante reste, intacte
    # Le repository n'a été interrogé QUE sur le delta de ce run.
    assert pending.promotable_calls[-1] == frozenset({f"LEGIARTI{B}"})


async def test_a_pending_seen_again_keeps_its_birth_date(
    service, graph, pending, context
) -> None:  # noqa: ANN001
    """``first_seen_run`` ne bouge jamais : c'est la date de naissance du trou.

    Sans ça, une pendante rencontrée à chaque run paraîtrait éternellement neuve,
    et « depuis quand ce lien manque-t-il ? » n'aurait pas de réponse.
    """
    await graph.merge_document_node(_doc(A))
    first = PipelineContext.create(sources=(SourceName.LEGI,))
    second = PipelineContext.create(sources=(SourceName.LEGI,))

    await service.execute([_rel(A, MISSING)], set(), first)
    await service.execute([_rel(A, MISSING)], set(), second)

    assert len(pending.pendings) == 1  # union idempotente : pas de doublon
    stored = next(iter(pending.pendings.values()))
    assert stored.first_seen_run == first.run_id
    assert stored.last_seen_run == second.run_id


async def test_an_empty_phase_two_is_a_legal_run(service, context) -> None:  # noqa: ANN001
    outcome = await service.execute([], set(), context)

    assert outcome.written_count == 0
    assert outcome.pending_count == 0
    assert outcome.promoted_count == 0
