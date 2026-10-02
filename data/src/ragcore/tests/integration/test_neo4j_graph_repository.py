"""Le dépôt de graphe contre un vrai Neo4j : un fake ne ferait que rejouer notre lecture
de Cypher.

L'affirmation à prouver : un ``MATCH`` sans résultat réussit sans rien écrire, et
``result.single()`` rend ``None``, donc l'arête ressort en ``pending``.
"""

from datetime import UTC, datetime

import pytest
from neo4j.exceptions import ConstraintError
from testcontainers.neo4j import Neo4jContainer

from ragcore.adapters.storage.neo4j.client import create_neo4j_driver
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.neo4j.schema import ensure_graph_constraints
from ragcore.core.links import CITE
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.relation import Relation

pytestmark = pytest.mark.integration

RUN = RunId("run-1")


def _doc(n: int) -> ParsedDocument:
    return ParsedDocument(
        identifier=Identifier(raw=f"LEGIARTI{n:012d}"),
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title=f"Article {n}",
        content=f"contenu {n}",
        structure={},
        metadata={},
        parsed_at=datetime.now(UTC),
    )


def _relation(source: int, target: int) -> Relation:
    return Relation(
        source_identifier=Identifier(raw=f"LEGIARTI{source:012d}"),
        target_identifier=Identifier(raw=f"LEGIARTI{target:012d}"),
        relation_type=CITE,
        source=SourceName.LEGI,
        metadata={},
    )


NEO4J_IMAGE = "neo4j:2025.09.0"
"""La version de production (``docker-compose.base.yml``) : le type d'arête dynamique
est un fait mesuré sur une version, pas garanti sur toutes."""


@pytest.fixture(scope="module")
def neo4j_url():
    with Neo4jContainer(NEO4J_IMAGE) as container:
        yield container.get_connection_url(), container.password


@pytest.fixture
async def repo(neo4j_url):
    url, password = neo4j_url
    driver = create_neo4j_driver(url, "neo4j", password)
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    await ensure_graph_constraints(driver)
    repository = Neo4jGraphRepository(driver)
    yield repository
    await driver.close()


async def _edge_types(repo) -> list[str]:
    """Interroge Neo4j, pas l'objet Python : le verbe doit être la structure du graphe."""
    async with repo._driver.session() as session:  # noqa: SLF001 — on inspecte le graphe, pas le repo
        result = await session.run("MATCH ()-[r]->() RETURN type(r) AS t")
        return sorted([record["t"] async for record in result])


async def test_the_verb_IS_the_edge_type(repo) -> None:
    """Le verbe est le type d'arête, pas une propriété : ``MATCH (a)-[:cite]->(b)`` est
    une traversée native. Un mot brut non traduit devient un type d'arête lui aussi."""
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))
    await repo.merge_document_node(_doc(3))

    canonical = _relation(1, 2)  # cite
    raw = Relation(
        source_identifier=Identifier(raw=f"LEGIARTI{1:012d}"),
        target_identifier=Identifier(raw=f"LEGIARTI{3:012d}"),
        relation_type="ZORGLUB",  # normalisé à la frontière du modèle
        source=SourceName.LEGI,
        metadata={"typelien": "ZORGLUB"},
    )

    result = await repo.upsert_relations([canonical, raw], RUN)
    assert len(result.written) == 2, "les deux arêtes sont écrites"

    # Neo4j écrit le type tel quel, sans le majusculer : `:cite` n'est qu'un usage
    assert await _edge_types(repo) == ["cite", "zorglub"], (
        "le verbe EST le type d'arête — et le mot brut y a droit "
        "au même titre que le verbe canonique"
    )


async def test_an_edge_whose_target_is_missing_comes_back_as_pending(repo) -> None:
    """Une arête vers une cible absente ressort en ``pending``, sans disparaître."""
    await repo.merge_document_node(_doc(1))  # la source existe
    # ... mais pas la cible : le document 2 n'a jamais été ingéré.

    result = await repo.upsert_relations([_relation(1, 2)], RUN)

    assert result.written == []
    assert len(result.pending) == 1
    assert result.pending[0].target_identifier.raw == "LEGIARTI000000000002"


async def test_an_edge_between_two_existing_nodes_is_written(repo) -> None:
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))

    result = await repo.upsert_relations([_relation(1, 2)], RUN)

    assert len(result.written) == 1
    assert result.pending == []


async def test_nothing_is_lost_between_input_and_output(repo) -> None:
    """``len(written) + len(pending) == len(entrée)`` : une relation est écrite ou
    différée, jamais évaporée."""
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))
    relations = [_relation(1, 2), _relation(1, 99), _relation(2, 98)]

    result = await repo.upsert_relations(relations, RUN)

    assert len(result.written) + len(result.pending) == len(relations)
    assert len(result.written) == 1  # seule 1->2 a ses deux extrémités
    assert len(result.pending) == 2


async def test_a_pending_edge_becomes_written_once_its_target_arrives(repo) -> None:
    """La promotion, contre la vraie base : le rejeu n'est pas une fiction."""
    await repo.merge_document_node(_doc(1))
    first = await repo.upsert_relations([_relation(1, 2)], RUN)
    assert len(first.pending) == 1

    await repo.merge_document_node(_doc(2))  # la cible arrive enfin
    second = await repo.upsert_relations([_relation(1, 2)], RUN)

    assert len(second.written) == 1
    assert second.pending == []


async def test_upserting_the_same_edge_twice_creates_one_edge(repo) -> None:
    """``MERGE``, pas ``CREATE`` : rejouer un run ne double pas le graphe. L'identité de
    l'arête est son verbe."""
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))

    await repo.upsert_relations([_relation(1, 2)], RUN)
    await repo.upsert_relations([_relation(1, 2)], RUN)

    assert await _edge_types(repo) == ["cite"], "une seule arête, pas deux"


async def test_existing_node_ids_returns_only_what_exists(repo) -> None:
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))

    found = await repo.existing_node_ids(
        [
            Identifier(raw="LEGIARTI000000000001"),
            Identifier(raw="LEGIARTI000000000099"),
        ],
    )

    assert found == {"LEGIARTI000000000001"}


async def test_deleting_outgoing_edges_preserves_the_node(repo) -> None:
    """Seules les sortantes partent : les entrantes viennent d'autres documents."""
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))
    await repo.upsert_relations([_relation(1, 2)], RUN)

    await repo.delete_relations_from(
        Identifier(raw="LEGIARTI000000000001"), SourceName.LEGI
    )

    remaining = await repo.existing_node_ids(
        [
            Identifier(raw="LEGIARTI000000000001"),
            Identifier(raw="LEGIARTI000000000002"),
        ],
    )
    assert remaining == {"LEGIARTI000000000001", "LEGIARTI000000000002"}

    # Compté sans nommer de type : le verbe est le type d'arête
    assert await _edge_types(repo) == [], "les arêtes sortantes sont parties…"
    # …et les nœuds, eux, sont restés (assertion ci-dessus).


# --- La compensation par run, contre la vraie base ---------------------------------


async def _edge_count(repo) -> int:
    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run("MATCH ()-[r]->() RETURN count(r) AS n")
        ).single()
    return record["n"]


async def test_delete_by_run_removes_only_this_runs_edges(repo) -> None:
    """Deux runs écrivent depuis le même document : compenser l'un ne défait que ses
    arêtes."""
    for n in (1, 2, 3):
        await repo.merge_document_node(_doc(n))

    run_a = RunId("run-A")
    run_b = RunId("run-B")

    # Le document 1 cite le 2 dans le run A, et le 3 dans le run B
    await repo.upsert_relations([_relation(1, 2)], run_a)
    await repo.upsert_relations([_relation(1, 3)], run_b)
    assert await _edge_count(repo) == 2

    # On compense le run A : 1→2 part, 1→3 reste
    await repo.delete_relations_by_run(run_a)

    assert await _edge_count(repo) == 1, "seule l'arête du run A est défaite"
    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run(
                "MATCH (a)-[r]->(b) RETURN b.identifier AS cible, r.run_id AS run"
            )
        ).single()
    assert record["cible"] == "LEGIARTI000000000003"
    assert record["run"] == run_b, "l'arête survivante est bien celle du run B"


async def test_a_node_carries_Document_and_its_type(repo) -> None:
    await repo.merge_document_node(_doc(1))

    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run(
                "MATCH (n {identifier: 'LEGIARTI000000000001'}) RETURN labels(n) AS l"
            )
        ).single()
    assert set(record["l"]) == {"Document", "Article"}


async def test_the_constraint_refuses_a_second_node_with_the_same_identifier(
    repo,
) -> None:
    """L'unicité est garantie par la base, pas seulement par le ``MERGE``."""
    await repo.merge_document_node(_doc(1))

    async with repo._driver.session() as session:  # noqa: SLF001
        with pytest.raises(ConstraintError):
            await session.run("CREATE (:Document {identifier: 'LEGIARTI000000000001'})")


async def test_a_lookup_by_identifier_uses_the_index(repo) -> None:
    """Sans le label ``Document``, la recherche parcourrait tous les nœuds."""
    async with repo._driver.session() as session:  # noqa: SLF001
        result = await session.run(
            "EXPLAIN MATCH (n:Document {identifier: $id}) RETURN n", id="x"
        )
        summary = await result.consume()

    assert "NodeUniqueIndexSeek" in str(summary.plan)
