"""Implémentation Neo4j du GraphRepository.

Un nœud est identifié par son seul ``identifier`` sérialisé (p. ex.
``LEGIARTI000006419264``) — jamais par un champ deviné parmi plusieurs candidats : un
identifiant unique et explicite est ce qui rend le ``MERGE`` déterministe. Le label du
nœud vient de la table ``NodeLabels``, d'après les 8 lettres de l'identifiant.
"""

import neo4j

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier, RunId
from ragcore.core.models.relation import Relation
from ragcore.core.ports.graph_repository import RelationWriteResult

from .node_properties import NodeHydration, NodeLabels, node_props

__all__ = ["Neo4jGraphRepository", "NodeHydration", "NodeLabels"]


_MERGE_NODE = (
    "MERGE (d {identifier: $identifier}) SET d:$($label) SET d += $props RETURN d"
)


class Neo4jGraphRepository:
    """Neo4j implementation of GraphRepository.

    Utilise `identifier` (sérialisé) comme champ clé unique pour tous les nœuds.
    """

    def __init__(
        self,
        driver: neo4j.AsyncDriver,
        labels: NodeLabels,
        hydration: NodeHydration | None = None,
    ) -> None:
        self._driver = driver
        self._labels = labels
        # Défaut = régime prod (nœud maigre). Le hook passe l'hydratation de dev.
        self._hydration = hydration or NodeHydration()

    async def merge_document_node(self, document: ParsedDocument) -> None:
        """Merge un nœud document. Le label vient de ``NodeLabels``, d'après l'identifiant.

        **Le ``MERGE`` ne porte PAS le label — et c'est le point.** ``MERGE`` matche le
        motif ENTIER, label compris : ``MERGE (d:Article {identifier: X})`` ne retrouve
        pas un nœud du même identifiant portant un autre label, et en crée un SECOND. On
        ``MERGE`` donc sur le seul ``identifier``, ce qui retombe sur le nœud existant
        quel que soit son label, PUIS on pose le label réel.
        """
        async with self._driver.session() as session:
            await session.run(
                _MERGE_NODE,
                identifier=document.identifier.serialize(),
                label=self._labels.label_for(document.identifier),
                props=node_props(document, self._hydration),
            )

    async def upsert_relations(
        self, relations: list[Relation], run_id: RunId
    ) -> RelationWriteResult:
        """Crée ou met à jour les relations, et rapporte celles qui n'ont pas pris.

        **Le type d'arête est le VERBE, et c'est le point.** L'ancienne version écrivait
        toutes les arêtes sous un type constant ``:REFERENCES`` et rangeait le verbe réel
        dans une *propriété*. Le graphe n'avait alors qu'un seul type de lien : le
        voisinage du serving (le rôle même de Neo4j ici) devait scanner **toutes** les
        arêtes puis filtrer sur une propriété, là où ``MATCH (a)-[:CITES]->(b)`` est une
        traversée native indexée. Le verbe était une donnée *dans* le graphe au lieu
        d'être la *structure* du graphe.

        ``MERGE (a)-[r:$($relation_type)]->(b)`` — le type d'arête paramétré, natif
        depuis Cypher 5.26 (vérifié aussi sur 2025.09, sans APOC). La sûreté ne vient pas
        d'un échappement : elle vient du type. ``Relation.relation_type`` est un
        ``ValidatedVerb`` — il ne peut pas contenir autre chose que
        ``[a-z][a-z0-9_]*``, donc il n'y a rien à injecter.

        Un ``MATCH`` qui ne matche pas produit zéro ligne : la requête réussit, ne lève
        rien, et n'écrit rien. Le ``RETURN r`` était déjà là — il n'était simplement
        jamais lu, et l'arête disparaissait en silence. Le consommer suffit à distinguer
        l'écrit du différé.
        """
        written: list[Relation] = []
        pending: list[Relation] = []

        # La cible IDENTIFIÉE doit exister : `MATCH (b)`. Si le document cité n'est pas
        # (encore) dans le corpus, la requête ne rend rien et l'arête part au cache des
        # pendantes (§13) — elle sera rejouée quand la cible arrivera.
        matched = (
            "MATCH (a {identifier: $source_identifier})"
            " MATCH (b {identifier: $target_identifier})"
            " MERGE (a)-[r:$($relation_type)]->(b)"
            " SET r += $props SET r.run_id = $run_id RETURN r"
        )

        # Il n'y a plus qu'un cas. Une cible DÉCRITE ne devient plus une arête vers un
        # placeholder : elle est une relation non formatée (ADR-045), écrite dans Mongo
        # et jamais dans le graphe. Toute relation qui arrive ici a donc une cible
        # identifiée, et le seul motif légitime est le `MATCH`.
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
        """Les identifiants (sérialisés) qui existent bel et bien comme nœuds."""
        if not identifiers:
            return set()

        query = (
            "MATCH (n) WHERE n.identifier IN $identifiers"
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
        """Supprime les seules relations SORTANTES du nœud, sans toucher au nœud.

        Le ``MATCH`` porte sur l'``identifier`` sérialisé — la même clé que ``merge``, donc
        on retrouve exactement le nœud écrit. Ne supprimer que le sortant préserve les
        arêtes qu'un AUTRE document a posées vers celui-ci.
        """
        identifier_value = identifier.serialize()

        query = "MATCH (d {identifier: $identifier})-[r]->() DELETE r"
        async with self._driver.session() as session:
            await session.run(
                query,
                identifier=identifier_value,
            )

    async def delete_relations_by_run(self, run_id: RunId) -> None:
        """Détache les arêtes taguées de ce ``run_id`` — et elles seules (§8).

        La maille de compensation. ``upsert_relations`` pose ``r.run_id`` sur chaque
        arête écrite ; ici on ne défait QUE celles-là. La différence avec
        ``delete_relations_from`` est le cœur du §8 : cette dernière supprime *toutes*
        les sortantes d'un nœud, quel qu'en soit l'auteur — un run rejoué emporterait les
        arêtes qu'un autre run avait posées. Filtrer sur ``run_id`` borne la suppression
        à l'ouvrage du run, exactement.
        """
        query = "MATCH ()-[r]->() WHERE r.run_id = $run_id DELETE r"
        async with self._driver.session() as session:
            await session.run(query, run_id=run_id)

    async def drop_all(self) -> None:
        """Detach-delete every node and relation. Irreversible."""
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
