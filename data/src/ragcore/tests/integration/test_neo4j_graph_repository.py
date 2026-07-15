"""Le §12 contre un VRAI Neo4j — le seul endroit où il puisse être prouvé.

``InMemoryGraphRepository`` rejoue ma *lecture* de Cypher. Si j'ai mal lu Cypher,
le fake ment avec moi : il confirmerait mon erreur au lieu de l'attraper. Toute la
doctrine du comptage exact repose sur une affirmation qu'aucun test unitaire ne
peut trancher —

    un ``MATCH`` qui ne matche pas produit ZÉRO ligne : la requête réussit, ne lève
    rien, et n'écrit rien.

C'est de là que venait le mensonge (``count=len(relations)`` = les relations
*tentées*). Ce fichier vérifie que ``result.single()`` rend bien ``None`` dans ce
cas, donc que l'arête ressort en ``pending`` au lieu de s'évaporer.
"""

from datetime import UTC, datetime

import pytest
from testcontainers.neo4j import Neo4jContainer

from ragcore.adapters.storage.neo4j.client import create_neo4j_driver
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.core.links import CITES
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import ELI, OwnerId, RunId, UnknownRef
from ragcore.core.models.relation import Relation

pytestmark = pytest.mark.integration

OWNER = OwnerId("owner-1")
OTHER_OWNER = OwnerId("owner-2")
RUN = RunId("run-1")


def _doc(n: int) -> ParsedDocument:
    return ParsedDocument(
        identifier=ELI(raw=f"LEGIARTI{n:012d}"),
        owner_id=OWNER,
        source=SourceName.LEGI,
        title=f"Article {n}",
        content=f"contenu {n}",
        structure={},
        metadata={},
        parsed_at=datetime.now(UTC),
    )


def _relation(source: int, target: int, owner: OwnerId = OWNER) -> Relation:
    return Relation(
        source_identifier=ELI(raw=f"LEGIARTI{source:012d}"),
        target_identifier=ELI(raw=f"LEGIARTI{target:012d}"),
        relation_type=CITES,
        owner_id=owner,
        source=SourceName.LEGI,
        metadata={},
    )


NEO4J_IMAGE = "neo4j:2025.09.0"
"""**La version de la PRODUCTION** (``docker-compose.base.yml``), pas une autre.

Elle était figée à ``5.26`` : on validait donc le dépôt contre un moteur que personne ne
fait tourner. Le type d'arête dynamique (``MERGE (a)-[r:$($verb)]->(b)``) marche sur les
deux — mais c'est un fait *mesuré*, pas un fait *garanti*, et une divergence de version
entre le test et la production est précisément ce qui transforme un fait mesuré en
mauvaise surprise.
"""


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
    repository = Neo4jGraphRepository(driver)
    yield repository
    await driver.close()


async def _edge_types(repo) -> list[str]:
    """Les types d'arête RÉELLEMENT écrits dans le graphe.

    On interroge Neo4j, pas l'objet Python : c'est la seule façon de prouver que le verbe
    est devenu la *structure* du graphe et pas une simple propriété portée par lui.
    """
    async with repo._driver.session() as session:  # noqa: SLF001 — on inspecte le graphe, pas le repo
        result = await session.run("MATCH ()-[r]->() RETURN type(r) AS t")
        return sorted([record["t"] async for record in result])


async def test_a_described_target_becomes_a_node_instead_of_a_pending_edge(repo) -> None:
    """LE test du lot juri, contre une vraie base. Sans lui, le graphe serait vide.

    **La mesure qui a imposé ce chemin.** Les 68 ``<LIEN>`` du corpus de jurisprudence ont
    tous leurs attributs vides : ni ``id``, ni ``cidtexte``. Ils portent du texte —
    « Articles 1103 et 1229 du code civil ». La cour *décrit* l'article qu'elle vise.

    **Pourquoi une pendante (§13) ne convient PAS ici**, et c'est le point subtil. Une
    pendante est une arête dont la cible *n'est pas encore arrivée* : on l'attend, et un
    run futur la résoudra. Mais « Articles 1103 du code civil » **n'arrivera jamais** — ce
    n'est pas un document du corpus, c'est une phrase. La traiter comme une pendante la
    condamnerait à l'être éternellement, et le graphe juri resterait vide en attendant un
    événement impossible.

    On **crée** donc la cible (``MERGE (b:Unknown)``), et le nœud porte la phrase. La
    citation existe, elle est interrogeable, et la passe de résolution (extracteur de
    références + registre d'alias) la fusionnera plus tard vers le vrai article — **sans
    re-ingérer quoi que ce soit**, puisque le texte est déjà dans le graphe.
    """
    await repo.merge_document_node(_doc(1))  # l'arrêt

    citation = Relation(
        source_identifier=ELI(raw=f"LEGIARTI{1:012d}"),
        target_identifier=UnknownRef(raw="Articles 1103 et 1229 du code civil."),
        relation_type="cites",
        owner_id=OWNER,
        source=SourceName.CASS,
        metadata={"typelien": "CITATION"},
    )

    result = await repo.upsert_relations([citation], RUN)

    assert len(result.written) == 1, "la citation est ÉCRITE…"
    assert result.pending == [], "…et surtout PAS mise en attente d'un document fantôme"

    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run(
                "MATCH (a)-[r:cites]->(b:Unknown) RETURN b.text AS texte, b.identifier AS id"
            )
        ).single()

    assert record is not None, "le nœud :Unknown doit exister"
    assert record["texte"] == "Articles 1103 et 1229 du code civil.", (
        "et il porte la PHRASE — c'est elle que la passe de résolution lira"
    )
    assert record["id"].startswith("unknown:")


async def test_the_verb_IS_the_edge_type(repo) -> None:
    """LE test du lot, côté graphe. Le verbe est la STRUCTURE, pas une propriété.

    L'ancienne version écrivait **toutes** les arêtes sous un type constant
    ``:REFERENCES`` et rangeait le verbe réel dans une propriété ``relation_type``. Le
    graphe n'avait alors qu'un seul type de lien.

    Ce n'est pas un détail de style. Dans Neo4j, le **type d'arête est ce qui est indexé
    et traversable** : ``MATCH (a)-[:CITES]->(b)`` est une opération native, là où
    ``MATCH (a)-[r:REFERENCES]->(b) WHERE r.relation_type = 'cites'`` balaye toutes les
    arêtes du graphe avant de filtrer. Le voisinage est *le* rôle de Neo4j ici — c'est là
    que se paie le soin mis à l'extraction des liens.

    Un verbe canonique et un mot brut non traduit deviennent tous deux un type d'arête :
    le graphe porte ``ZORGLUB`` comme il porte ``CITES``, et le serving peut ignorer ce
    qu'il ne comprend pas — ce qu'il ne pourrait pas faire d'une arête inexistante.
    """
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))
    await repo.merge_document_node(_doc(3))

    canonical = _relation(1, 2)  # cites
    raw = Relation(
        source_identifier=ELI(raw=f"LEGIARTI{1:012d}"),
        target_identifier=ELI(raw=f"LEGIARTI{3:012d}"),
        relation_type="ZORGLUB",  # normalisé à la frontière du modèle
        owner_id=OWNER,
        source=SourceName.LEGI,
        metadata={"typelien": "ZORGLUB"},
    )

    result = await repo.upsert_relations([canonical, raw], RUN)
    assert len(result.written) == 2, "les deux arêtes sont écrites"

    # Mesuré : Neo4j écrit le type d'arête TEL QUEL, sans le majusculer. La convention
    # `:CITES` de la documentation Cypher est un usage, pas une contrainte du moteur — et
    # c'est bien le verbe normalisé de `ValidatedVerb` qui atterrit dans le graphe.
    assert await _edge_types(repo) == ["cites", "zorglub"], (
        "le verbe EST le type d'arête — et le mot brut y a droit "
        "au même titre que le verbe canonique"
    )


async def test_an_edge_whose_target_is_missing_comes_back_as_pending(repo) -> None:
    """LE test du §12. Sur l'ancien code, cette arête disparaissait en silence."""
    await repo.merge_document_node(_doc(1))  # la source existe
    # ... mais PAS la cible : le document 2 n'a jamais été ingéré.

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
    """L'invariant du port : ``len(written) + len(pending) == len(entrée)``.

    C'est lui qui rend le comptage exact possible : une relation est écrite ou
    différée, jamais évaporée.
    """
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
    """``MERGE``, pas ``CREATE`` : rejouer un run ne doit pas doubler le graphe.

    Le ``MERGE`` porte désormais sur ``(a)-[:cites]->(b)`` — l'identité de l'arête *est*
    son verbe. Auparavant elle portait sur ``(a)-[:REFERENCES {relation_type}]->(b)`` :
    l'unicité venait d'une propriété. Les deux sont idempotents, mais pour des raisons
    différentes, et c'est bien la nouvelle qu'on vérifie ici.
    """
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))

    await repo.upsert_relations([_relation(1, 2)], RUN)
    await repo.upsert_relations([_relation(1, 2)], RUN)

    assert await _edge_types(repo) == ["cites"], "une seule arête, pas deux"


async def test_an_edge_never_crosses_owners(repo) -> None:
    """Le nœud cible existe — mais chez QUELQU'UN D'AUTRE. L'arête ne doit pas
    s'écrire : sans le filtre owner_id, un graphe emprunterait les nœuds d'un autre.
    """
    await repo.merge_document_node(_doc(1))
    other = _doc(2).model_copy(update={"owner_id": OTHER_OWNER})
    await repo.merge_document_node(other)

    result = await repo.upsert_relations([_relation(1, 2, owner=OWNER)], RUN)

    assert result.written == []
    assert len(result.pending) == 1


async def test_existing_node_ids_returns_only_what_exists(repo) -> None:
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))

    found = await repo.existing_node_ids(
        [ELI(raw="LEGIARTI000000000001"), ELI(raw="LEGIARTI000000000099")], OWNER
    )

    assert found == {"eli:LEGIARTI000000000001"}


async def test_deleting_outgoing_edges_preserves_the_node(repo) -> None:
    """Neo4j est en position terminale : ses arêtes ENTRANTES viennent d'autres
    documents. Supprimer le nœud les emporterait — d'où le delete ciblé.
    """
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))
    await repo.upsert_relations([_relation(1, 2)], RUN)

    await repo.delete_relations_from(ELI(raw="LEGIARTI000000000001"), OWNER, SourceName.LEGI)

    remaining = await repo.existing_node_ids(
        [ELI(raw="LEGIARTI000000000001"), ELI(raw="LEGIARTI000000000002")], OWNER
    )
    assert remaining == {"eli:LEGIARTI000000000001", "eli:LEGIARTI000000000002"}

    # Compté SANS nommer de type : `MATCH ()-[r:REFERENCES]->()` — ce que ce test faisait
    # — ne compte plus rien depuis que le verbe est le type d'arête. Il aurait donc validé
    # un `delete_relations_from` qui ne supprime RIEN. Un test qui n'observe pas ce qu'il
    # prétend observer est pire qu'un test absent : il rassure.
    assert await _edge_types(repo) == [], "les arêtes sortantes sont parties…"
    # …et les nœuds, eux, sont restés (assertion ci-dessus).


# --- §8 : la compensation à la maille du run, contre la vraie base -------------------


async def _edge_count(repo) -> int:
    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run("MATCH ()-[r]->() RETURN count(r) AS n")
        ).single()
    return record["n"]


async def _labels_of(repo, identifier: str) -> set[str]:
    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run(
                "MATCH (n {identifier: $id}) RETURN labels(n) AS labels",
                id=identifier,
            )
        ).single()
    return set(record["labels"]) if record is not None else set()


async def test_delete_by_run_removes_only_this_runs_edges(repo) -> None:
    """LE test du §8. Deux runs écrivent depuis le MÊME document ; compenser l'un ne
    doit défaire QUE ses arêtes, jamais celles de l'autre.

    C'est exactement ce que ``delete_relations_from`` ne sait pas faire : il supprime
    toutes les sortantes du nœud, sans distinguer l'auteur. Sur cette confusion, un run
    rejoué emporterait l'ouvrage d'un run précédent — la sur-suppression que la maille
    par ``run_id`` supprime.
    """
    for n in (1, 2, 3):
        await repo.merge_document_node(_doc(n))

    run_a = RunId("run-A")
    run_b = RunId("run-B")

    # Le document 1 cite le 2 dans le run A, et le 3 dans le run B.
    await repo.upsert_relations([_relation(1, 2)], run_a)
    await repo.upsert_relations([_relation(1, 3)], run_b)
    assert await _edge_count(repo) == 2

    # On compense le run A. Son arête (1→2) part ; celle du run B (1→3) reste.
    await repo.delete_relations_by_run(run_a, OWNER)

    assert await _edge_count(repo) == 1, "seule l'arête du run A est défaite"
    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run(
                "MATCH (a)-[r]->(b) RETURN b.identifier AS cible, r.run_id AS run"
            )
        ).single()
    assert record["cible"] == "eli:LEGIARTI000000000003"
    assert record["run"] == run_b, "l'arête survivante est bien celle du run B"


async def test_delete_by_run_is_scoped_to_owner(repo) -> None:
    """Deux tenants pourraient partager un ``run_id`` (rien ne l'interdit). La
    compensation d'un run reste bornée à son propriétaire.

    Chaque tenant a SON arête (une arête ne traverse pas les propriétaires — cf.
    ``test_an_edge_never_crosses_owners``), et les deux partagent le même ``run_id``.
    Compenser ce run chez OTHER_OWNER ne doit défaire que l'arête d'OTHER_OWNER.
    """
    # Deux nœuds chez OWNER, deux nœuds chez OTHER_OWNER.
    await repo.merge_document_node(_doc(1))
    await repo.merge_document_node(_doc(2))
    await repo.merge_document_node(_doc(3).model_copy(update={"owner_id": OTHER_OWNER}))
    await repo.merge_document_node(_doc(4).model_copy(update={"owner_id": OTHER_OWNER}))

    # Une arête par tenant, sous le MÊME run_id.
    await repo.upsert_relations([_relation(1, 2)], RUN)  # chez OWNER
    await repo.upsert_relations([_relation(3, 4, owner=OTHER_OWNER)], RUN)  # chez OTHER
    assert await _edge_count(repo) == 2

    await repo.delete_relations_by_run(RUN, OTHER_OWNER)  # on ne compense QU'OTHER

    assert await _edge_count(repo) == 1, "l'arête d'OWNER n'est pas touchée"
    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run("MATCH ()-[r]->() RETURN r.owner_id AS owner")
        ).single()
    assert record["owner"] == OWNER, "l'arête survivante est celle d'OWNER"


async def test_compensating_an_orphan_node_deletes_it(repo) -> None:
    """Un nœud que personne ne cite n'existait que pour son document : ``DETACH DELETE``.

    C'est la fin du ``_noop`` : un merge de nœud qui ne va pas au bout de sa saga ne
    laisse plus un orphelin derrière lui.
    """
    await repo.merge_document_node(_doc(1))

    await repo.compensate_document_node(ELI(raw="LEGIARTI000000000001"), OWNER)

    remaining = await repo.existing_node_ids([ELI(raw="LEGIARTI000000000001")], OWNER)
    assert remaining == set(), "le nœud orphelin est supprimé"


async def test_compensating_a_cited_node_dehydrates_it(repo) -> None:
    """Un nœud CITÉ par un autre document ne peut pas être supprimé : sa citation
    entrante mourrait avec lui. On le dé-hydrate en ``:Unknown`` — il survit comme
    cible décrite, exactement le statut d'une citation non encore résolue.
    """
    await repo.merge_document_node(_doc(1))  # le citant
    await repo.merge_document_node(_doc(2))  # le cité, qu'on va compenser
    await repo.upsert_relations([_relation(1, 2)], RUN)  # 1 cite 2 : arête entrante sur 2

    await repo.compensate_document_node(ELI(raw="LEGIARTI000000000002"), OWNER)

    # Le nœud SURVIT (la citation de 1 pointe encore dessus)…
    remaining = await repo.existing_node_ids([ELI(raw="LEGIARTI000000000002")], OWNER)
    assert remaining == {"eli:LEGIARTI000000000002"}, "le nœud cité n'est pas supprimé"

    # …mais dé-hydraté : il a perdu son label métier (`Article`) pour `:Unknown`, et son
    # contenu de document (`title`, `source`) a disparu — il n'est plus qu'une cible.
    labels = await _labels_of(repo, "eli:LEGIARTI000000000002")
    assert labels == {"Unknown"}, "le nœud cité est ramené au statut de cible décrite"

    async with repo._driver.session() as session:  # noqa: SLF001
        record = await (
            await session.run(
                "MATCH (n {identifier: 'eli:LEGIARTI000000000002'})"
                " RETURN n.title AS title, n.source AS source, n.text AS text"
            )
        ).single()
    assert record["title"] is None and record["source"] is None, (
        "les propriétés de document sont retirées"
    )
    assert record["text"] is not None, "il porte un texte, comme toute cible :Unknown"

    # …et la citation entrante, elle, tient toujours.
    assert await _edge_count(repo) == 1


async def test_compensating_an_absent_node_is_a_noop(repo) -> None:
    """La saga peut échouer AVANT le merge du nœud : compenser un nœud qui n'existe
    pas ne doit pas lever. La compensation est idempotente — c'est ce que la saga
    attend d'un ``compensate``.
    """
    await repo.compensate_document_node(ELI(raw="LEGIARTI000000000404"), OWNER)
