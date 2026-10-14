"""Implémentation Neo4j du GraphRepository.

Un nœud est identifié par son seul ``identifier`` sérialisé et porte deux labels :
``Document``, qui porte la contrainte d'unicité, et celui de son ``document_type``.
"""

from collections import defaultdict
from collections.abc import Iterator
from typing import Any

import neo4j

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.relation import Relation
from ragcore.core.ports.graph_repository import RelationWriteResult

from .node_properties import DOCUMENT_LABEL, TYPE_LABELS, NodeHydration, node_props

__all__ = ["Neo4jGraphRepository", "NodeHydration"]


_MERGE_NODE = (
    f"MERGE (d:{DOCUMENT_LABEL} {{identifier: $identifier}})"
    " SET d:$($label) SET d += $props RETURN d"
)


_RELATION_BATCH_SIZE = 5_000
"""Les arêtes d'une requête : assez pour amortir l'aller-retour, assez peu pour une
transaction légère."""

_UPSERT_RELATIONS = (
    "UNWIND $rows AS row"
    f" MATCH (a:{DOCUMENT_LABEL} {{identifier: row.source}})"
    f" MATCH (b:{DOCUMENT_LABEL} {{identifier: row.target}})"
    " MERGE (a)-[r:$($relation_type)]->(b)"
    " SET r += row.props SET r.run_id = $run_id"
    " RETURN row.index AS index"
)

Row = dict[str, Any]


def _batches(relations: list[Relation]) -> Iterator[tuple[str, list[Row]]]:
    """Les lignes d'un verbe, par lots. ``index`` est la position dans l'entrée."""
    by_type: dict[str, list[Row]] = defaultdict(list)
    for index, relation in enumerate(relations):
        by_type[relation.relation_type].append(
            {
                "index": index,
                "source": relation.source_identifier.serialize(),
                "target": relation.target_identifier.serialize(),
                "props": dict(relation.metadata),
            }
        )
    for relation_type, rows in by_type.items():
        for start in range(0, len(rows), _RELATION_BATCH_SIZE):
            yield relation_type, rows[start : start + _RELATION_BATCH_SIZE]


async def _write_batch(
    session: neo4j.AsyncSession, relation_type: str, rows: list[Row], run_id: RunId
) -> set[int]:
    """Rend les indices des arêtes écrites."""
    result = await session.run(
        _UPSERT_RELATIONS, rows=rows, relation_type=relation_type, run_id=run_id
    )
    return {record["index"] async for record in result}


class Neo4jGraphRepository:
    def __init__(
        self,
        driver: neo4j.AsyncDriver,
        hydration: NodeHydration | None = None,
    ) -> None:
        self._driver = driver
        # Défaut : nœud maigre, comme en prod
        self._hydration = hydration or NodeHydration()

    async def merge_document_node(self, document: ParsedDocument) -> None:
        """Le ``MERGE`` porte sur ``Document`` et ``identifier``, donc sur la contrainte
        d'unicité ; le label de type, déduit du préfixe, s'ajoute ensuite."""
        async with self._driver.session() as session:
            await session.run(
                _MERGE_NODE,
                identifier=document.identifier.serialize(),
                label=TYPE_LABELS[document.document_type],
                props=node_props(document, self._hydration),
            )

    async def upsert_relations(
        self, relations: list[Relation], run_id: RunId
    ) -> RelationWriteResult:
        """Par lots ``UNWIND`` d'un seul verbe : une requête par lot, pas par arête.

        Le type d'arête est le verbe, pour une traversée native
        (``MATCH (a)-[:cite]->(b)``). Le paramétrer (``$(...)``, Cypher 5.26+) est sûr :
        un ``ValidatedVerb`` n'a rien à injecter.

        Une ligne dont un ``MATCH`` échoue disparaît du lot sans erreur : seuls les
        indices rendus distinguent l'arête écrite de la différée.
        """
        written_indices: set[int] = set()
        async with self._driver.session() as session:
            for relation_type, rows in _batches(relations):
                written_indices |= await _write_batch(
                    session, relation_type, rows, run_id
                )
        return RelationWriteResult(
            written=[r for i, r in enumerate(relations) if i in written_indices],
            pending=[r for i, r in enumerate(relations) if i not in written_indices],
        )

    async def existing_node_ids(self, identifiers: list[Identifier]) -> set[str]:
        if not identifiers:
            return set()

        query = (
            f"MATCH (n:{DOCUMENT_LABEL}) WHERE n.identifier IN $identifiers"
            " RETURN n.identifier AS identifier"
        )
        async with self._driver.session() as session:
            result = await session.run(
                query,
                identifiers=[i.serialize() for i in identifiers],
            )
            return {record["identifier"] async for record in result}

    async def delete_relations_from(
        self, identifier: Identifier, source: SourceName
    ) -> None:
        """Les sortantes seulement : les arêtes posées par d'autres documents restent."""
        identifier_value = identifier.serialize()

        query = (
            f"MATCH (d:{DOCUMENT_LABEL} {{identifier: $identifier}})-[r]->() DELETE r"
        )
        async with self._driver.session() as session:
            await session.run(
                query,
                identifier=identifier_value,
            )

    async def delete_relations_by_run(self, run_id: RunId) -> None:
        """Les arêtes taguées de ce run, et elles seules."""
        query = "MATCH ()-[r]->() WHERE r.run_id = $run_id DELETE r"
        async with self._driver.session() as session:
            await session.run(query, run_id=run_id)

    async def drop_all(self) -> None:
        """Irréversible."""
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
