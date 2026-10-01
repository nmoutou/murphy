"""Implémentation Neo4j du GraphRepository.

Un nœud est identifié par son seul ``identifier`` sérialisé et porte deux labels :
``Document``, qui porte la contrainte d'unicité, et celui de son ``document_type``.
"""

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
        """Le type d'arête est le verbe, pour une traversée native
        (``MATCH (a)-[:CITES]->(b)``). Le paramétrer (``$(...)``, Cypher 5.26+) est sûr :
        un ``ValidatedVerb`` n'a rien à injecter.

        Un ``MATCH`` sans résultat réussit sans rien écrire : seul le ``RETURN r``
        distingue l'arête écrite de la différée.
        """
        written: list[Relation] = []
        pending: list[Relation] = []

        matched = (
            f"MATCH (a:{DOCUMENT_LABEL} {{identifier: $source_identifier}})"
            f" MATCH (b:{DOCUMENT_LABEL} {{identifier: $target_identifier}})"
            " MERGE (a)-[r:$($relation_type)]->(b)"
            " SET r += $props SET r.run_id = $run_id RETURN r"
        )

        async with self._driver.session() as session:
            for relation in relations:
                result = await session.run(
                    matched,
                    source_identifier=relation.source_identifier.serialize(),
                    target_identifier=relation.target_identifier.serialize(),
                    relation_type=relation.relation_type,
                    props=dict(relation.metadata),
                    run_id=run_id,
                )
                record = await result.single()
                if record is None:
                    pending.append(relation)
                else:
                    written.append(relation)

        return RelationWriteResult(written=written, pending=pending)

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
