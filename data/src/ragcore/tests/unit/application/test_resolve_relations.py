"""La phase 2 : le comptage exact, et les pendantes.

Invariant exécuté : ``written + pending == entrée``. Une arête dont une extrémité manque
est différée, jamais comptée comme écrite.
"""

import random
from datetime import UTC, datetime

import pytest

from ragcore.application import relation_writer, resolve_relations
from ragcore.application.resolve_relations import ResolveRelationsService
from ragcore.application.run_context import PipelineContext
from ragcore.core.exceptions import TransitNotDrainedError
from ragcore.core.links import CITE, CONTIENT
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.pending import PendingRelation
from ragcore.core.models.relation import Relation
from ragcore.core.services.relation_reduction import reduce_transitively
from ragcore.core.statistics_measures import COMPONENT_NODES, COMPONENT_RELATIONS
from ragcore.core.telemetry_events import (
    RELATION_PENDING,
    RELATION_PROMOTED,
    RELATION_UPSERTED,
)
from ragcore.tests.fakes import (
    InMemoryGraphRepository,
    InMemoryPendingRepository,
    InMemoryTransitRepository,
    RecordingTelemetry,
)

A, B, MISSING = "000000000001", "000000000002", "000000000404"


def _identifier(suffix: str) -> Identifier:
    return Identifier(raw=f"LEGIARTI{suffix}")


def _doc(suffix: str) -> ParsedDocument:
    return ParsedDocument(
        identifier=_identifier(suffix),
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
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
        relation_type=CITE,
        source=SourceName.LEGI,
    )


@pytest.fixture
def graph() -> InMemoryGraphRepository:
    return InMemoryGraphRepository()


@pytest.fixture
def pending() -> InMemoryPendingRepository:
    return InMemoryPendingRepository()


@pytest.fixture
def transit() -> InMemoryTransitRepository:
    return InMemoryTransitRepository()


@pytest.fixture
def telemetry() -> RecordingTelemetry:
    return RecordingTelemetry()


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext.create(sources=(SourceName.LEGI,))


@pytest.fixture
def service(graph, pending, transit, telemetry) -> ResolveRelationsService:  # noqa: ANN001
    return ResolveRelationsService(graph, pending, transit, telemetry)


async def _execute(
    service: ResolveRelationsService,
    relations: list[Relation],
    written_node_ids: set[str],
    context: PipelineContext,
):
    """La phase 1 a laissé ``relations`` en transit."""
    await service._transit_repo.insert_many(relations, context.run_id)  # noqa: SLF001
    components = await service.find_components(context)
    return await service.execute(components, written_node_ids, context)


async def test_a_resolvable_edge_is_written_and_counted(
    service, graph, telemetry, context
) -> None:  # noqa: ANN001
    await graph.merge_document_node(_doc(A))
    await graph.merge_document_node(_doc(B))

    outcome = await _execute(service, [_rel(A, B)], {f"LEGIARTI{A}"}, context)

    assert outcome.written_count == 1
    assert outcome.pending_count == 0
    events = telemetry.events_of(RELATION_UPSERTED)
    assert len(events) == 1
    assert events[0].payload["count"] == 1  # les arêtes écrites, pas tentées


async def test_an_unresolvable_edge_becomes_a_pending_not_a_silence(
    graph, pending, telemetry, context
) -> None:  # noqa: ANN001
    """La cible n'existe pas : rien n'est écrit, et la relation part en pendante."""
    service = ResolveRelationsService(
        graph, pending, InMemoryTransitRepository(), telemetry
    )
    await graph.merge_document_node(_doc(A))  # la cible MISSING n'est pas là

    outcome = await _execute(service, [_rel(A, MISSING)], set(), context)

    assert outcome.written_count == 0
    assert outcome.pending_count == 1
    assert graph.edges == []  # rien d'écrit dans le graphe
    assert len(pending.pendings) == 1  # mais la relation est gardée
    assert len(telemetry.events_of(RELATION_PENDING)) == 1
    assert telemetry.events_of(RELATION_UPSERTED) == []


async def test_nothing_is_lost_between_input_and_output(
    service, graph, context
) -> None:  # noqa: ANN001
    """``written + pending == entrée``."""
    await graph.merge_document_node(_doc(A))
    await graph.merge_document_node(_doc(B))
    relations = [_rel(A, B), _rel(A, MISSING), _rel(B, MISSING)]

    outcome = await _execute(service, relations, set(), context)

    assert outcome.written_count + outcome.pending_count == len(relations)


async def test_a_pending_is_promoted_when_its_target_finally_arrives(
    graph, pending, telemetry, context
) -> None:  # noqa: ANN001
    """La cible arrive au run suivant : la pendante est promue."""
    service = ResolveRelationsService(
        graph, pending, InMemoryTransitRepository(), telemetry
    )
    await graph.merge_document_node(_doc(A))
    await _execute(service, [_rel(A, B)], set(), context)  # B n'existe pas encore
    assert len(pending.pendings) == 1

    # Run suivant : B arrive
    await graph.merge_document_node(_doc(B))
    outcome = await _execute(service, [], {f"LEGIARTI{B}"}, context)

    assert outcome.promoted_count == 1
    assert pending.pendings == {}  # la pendante résolue quitte le cache
    assert len(graph.edges) == 1  # l'arête est enfin dans le graphe
    assert len(telemetry.events_of(RELATION_PROMOTED)) == 1


async def test_a_pending_is_promoted_when_its_source_finally_arrives(
    graph, pending, telemetry, context
) -> None:  # noqa: ANN001
    """``sens="cible"``, ancêtre, version précédente : le document courant est la cible
    de l'arête, et c'est la source qui manque."""
    service = ResolveRelationsService(
        graph, pending, InMemoryTransitRepository(), telemetry
    )
    await graph.merge_document_node(_doc(B))
    await _execute(service, [_rel(A, B)], {f"LEGIARTI{B}"}, context)
    assert len(pending.pendings) == 1

    await graph.merge_document_node(_doc(A))
    outcome = await _execute(service, [], {f"LEGIARTI{A}"}, context)

    assert outcome.promoted_count == 1
    assert pending.pendings == {}
    assert len(graph.edges) == 1


async def test_a_pending_born_in_this_run_is_not_replayed_in_it(
    service, graph, context
) -> None:  # noqa: ANN001
    """Elle naît quand tous les nœuds du run existent : la rejouer échouerait à coup
    sûr."""
    attempts: list[Relation] = []
    write = graph.upsert_relations

    async def spying_write(relations, run_id):  # noqa: ANN001, ANN202
        attempts.extend(relations)
        return await write(relations, run_id)

    graph.upsert_relations = spying_write
    await graph.merge_document_node(_doc(B))

    outcome = await _execute(service, [_rel(MISSING, B)], {f"LEGIARTI{B}"}, context)

    assert outcome.pending_count == 1
    assert outcome.promoted_count == 0
    assert attempts == [_rel(MISSING, B)]


async def test_a_pending_whose_other_end_is_still_missing_stays(
    service, graph, pending, context
) -> None:  # noqa: ANN001
    past = PipelineContext.create(sources=(SourceName.LEGI,))
    await pending.upsert_many(
        [PendingRelation.from_relation(_rel(A, MISSING), past.run_id)]
    )
    await graph.merge_document_node(_doc(A))

    outcome = await _execute(service, [], {f"LEGIARTI{A}"}, context)

    assert outcome.promoted_count == 0
    assert len(pending.pendings) == 1


async def test_replay_is_bounded_by_the_delta_not_the_backlog(
    service, graph, pending, context
) -> None:  # noqa: ANN001
    """Le rejeu ne vise que le delta du run, jamais tout le backlog."""
    await pending.upsert_many(
        [PendingRelation.from_relation(_rel(A, MISSING), context.run_id)]
    )
    await graph.merge_document_node(_doc(B))

    outcome = await _execute(service, [], {f"LEGIARTI{B}"}, context)

    assert outcome.promoted_count == 0
    assert len(pending.pendings) == 1  # la vieille pendante reste, intacte
    # Le dépôt n'a été interrogé que sur le delta de ce run
    assert pending.promotable_calls[-1] == frozenset({f"LEGIARTI{B}"})


async def test_a_pending_seen_again_keeps_its_birth_date(
    service, graph, pending, context
) -> None:  # noqa: ANN001
    """``first_seen_run`` ne bouge jamais : sinon « depuis quand ce lien manque-t-il ? »
    n'aurait pas de réponse."""
    await graph.merge_document_node(_doc(A))
    first = PipelineContext.create(sources=(SourceName.LEGI,))
    second = PipelineContext.create(sources=(SourceName.LEGI,))

    await _execute(service, [_rel(A, MISSING)], set(), first)
    await _execute(service, [_rel(A, MISSING)], set(), second)

    assert len(pending.pendings) == 1  # union idempotente : pas de doublon
    stored = next(iter(pending.pendings.values()))
    assert stored.first_seen_run == first.run_id
    assert stored.last_seen_run == second.run_id


async def test_an_empty_phase_two_is_a_legal_run(service, context) -> None:  # noqa: ANN001
    outcome = await _execute(service, [], set(), context)

    assert outcome.written_count == 0
    assert outcome.pending_count == 0
    assert outcome.promoted_count == 0


async def test_the_transit_is_drained_by_phase_two(
    service, graph, transit, context
) -> None:  # noqa: ANN001
    await graph.merge_document_node(_doc(A))
    await graph.merge_document_node(_doc(B))

    outcome = await _execute(service, [_rel(A, B), _rel(A, MISSING)], set(), context)

    assert outcome.extracted_count == 2
    assert await transit.count() == 0


async def test_a_relation_left_in_transit_fails_the_run(
    service, transit, context
) -> None:  # noqa: ANN001
    """Une ligne d'un autre run ne devrait pas exister : le vidage au démarrage l'aurait
    emportée. C'est un bug, pas un état dégradé (ADR-034 §6)."""
    stray = PipelineContext.create(sources=(SourceName.LEGI,))
    await transit.insert_many([_rel(A, B)], stray.run_id)

    with pytest.raises(TransitNotDrainedError, match="1 relation"):
        await _execute(service, [], set(), context)


# ── Par composantes connexes (ADR-034 §5) ─────────────────────────────────────


def _node(n: int) -> str:
    return f"LEGISCTA{n:012d}"


def _contains(source: int, target: int) -> Relation:
    return Relation(
        source_identifier=Identifier(raw=_node(source)),
        target_identifier=Identifier(raw=_node(target)),
        relation_type=CONTIENT,
        source=SourceName.LEGI,
    )


def _hierarchy_with_closures(seed: int) -> list[Relation]:
    """Des arbres de contenance, chacun déclaré avec sa fermeture (``<CONTEXTE>``), et
    des doublons."""
    rng = random.Random(seed)
    relations: list[Relation] = []
    for tree in range(6):
        base = tree * 100
        parents = {base + child: base + rng.randrange(child) for child in range(1, 20)}
        for child in parents:
            ancestor = child
            while ancestor in parents:
                ancestor = parents[ancestor]
                relations.append(_contains(ancestor, child))
    relations += relations[:5]
    rng.shuffle(relations)
    return relations


def _edges(relations: list[Relation]) -> set[tuple[str, str, str]]:
    return {
        (r.source_identifier.raw, r.target_identifier.raw, r.relation_type)
        for r in relations
    }


async def _with_nodes(
    graph: InMemoryGraphRepository, relations: list[Relation]
) -> None:
    for relation in relations:
        for identifier in (relation.source_identifier, relation.target_identifier):
            graph.nodes.add(identifier.serialize())


@pytest.mark.parametrize("seed", range(5))
async def test_reducing_component_by_component_is_the_global_reduction(
    service, graph, monkeypatch: pytest.MonkeyPatch, seed: int
) -> None:
    """Deux composantes n'ont aucun chemin commun : la réduction par composante est
    exactement celle du graphe entier, même lue par petits groupes et écrite par
    petits lots."""
    monkeypatch.setattr(resolve_relations, "_COMPONENT_READ_BUDGET", 7)
    monkeypatch.setattr(relation_writer, "_BUFFER_SIZE", 5)
    relations = _hierarchy_with_closures(seed) + [_rel(A, B)]
    await _with_nodes(graph, relations)
    context = PipelineContext.create(sources=(SourceName.LEGI,))

    outcome = await _execute(service, relations, set(), context)

    written = [relation for relation, _run_id in graph.edges]
    assert _edges(written) == _edges(reduce_transitively(relations))
    assert outcome.extracted_count == len(relations)
    assert (
        outcome.written_count + outcome.pending_count + outcome.reduced_count
        == outcome.extracted_count
    )


async def test_a_cycle_keeps_its_own_component_unreduced_and_only_it(
    service, graph, context
) -> None:
    """Un cycle de contenance rend la réduction indéfinie : sa composante est gardée
    telle quelle, les autres sont réduites. Réduit d'un bloc, le corpus entier aurait
    été gardé tel quel pour un seul cycle."""
    tree = [_contains(1, 2), _contains(2, 3), _contains(1, 3)]
    cycle = [_contains(8, 9), _contains(9, 8)]
    await _with_nodes(graph, tree + cycle)

    await _execute(service, tree + cycle, set(), context)

    written = [relation for relation, _run_id in graph.edges]
    assert _edges(written) == _edges(tree[:2] + cycle)


async def test_every_component_is_measured(service, graph, telemetry, context) -> None:
    relations = [_contains(1, 2), _contains(2, 3), _contains(1, 3), _contains(7, 8)]
    await _with_nodes(graph, relations)

    await _execute(service, relations, set(), context)

    assert telemetry.values_of(COMPONENT_NODES) == [3, 2]
    assert telemetry.values_of(COMPONENT_RELATIONS) == [3, 1]
    assert telemetry.snapshot_measures().distributions[COMPONENT_NODES].max_ref == (
        _node(1)
    )


async def test_a_transit_row_outlives_the_write_of_what_it_carries(
    graph, transit, telemetry, context
) -> None:
    """Supprimée avant l'écriture, une ligne serait perdue si l'écriture cassait."""
    seen_in_transit: list[int] = []
    write = graph.upsert_relations

    async def spying_write(relations, run_id):  # noqa: ANN001, ANN202
        seen_in_transit.append(await transit.count())
        return await write(relations, run_id)

    graph.upsert_relations = spying_write
    service = ResolveRelationsService(
        graph, InMemoryPendingRepository(), transit, telemetry
    )
    relations = [_contains(1, 2), _rel(A, B)]
    await _with_nodes(graph, relations)

    await _execute(service, relations, set(), context)

    assert seen_in_transit == [2]
    assert await transit.count() == 0
