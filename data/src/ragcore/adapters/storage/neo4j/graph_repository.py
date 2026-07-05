"""Implémentation Neo4j du GraphRepository.

Changements post-refonte :
- Identifiant unique : `identifier` (value=kind:raw, ex."eli:LEGIARTI...")
- Suppression de `source_id_fields` et des fallbacks dangereux (Bugs 2-3)
- Label dérivé du document.identifier.document_type
"""

import neo4j

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, SourceIdentifier
from ragcore.core.models.relation import Relation

# Labels Neo4j connus, utilisés pour la création des index
_KNOWN_LABELS = ("Document", "Article", "Texte", "Section")


class Neo4jGraphRepository:
    """Neo4j implementation of GraphRepository.
    
    Utilise `identifier` (sérialisé) comme champ clé unique pour tous les nœuds.
    """

    def __init__(self, driver: neo4j.AsyncDriver) -> None:
        self._driver = driver

    async def initialize(self) -> None:
        """Crée l'index Neo4j sur le champ `identifier`."""
        async with self._driver.session() as session:
            for label in _KNOWN_LABELS:
                await session.run(
                    f"CREATE INDEX IF NOT EXISTS"
                    f" FOR (n:{label}) ON (n.identifier)"
                )

    async def merge_document_node(self, document: ParsedDocument) -> None:
        """Merge un nœud document avec le label déduit de l'identifier.
        
        Le label est calculé depuis document.identifier.document_type (pour ELI).
        """
        # Déduire le label depuis l'identifier
        label = "Document"
        if hasattr(document.identifier, "document_type"):
            doc_type = document.identifier.document_type
            if doc_type and doc_type != "inconnu":
                label = doc_type.capitalize()

        identifier_value = document.identifier.serialize()

        query = (
            f"MERGE (d:{label} {{identifier: $identifier, owner_id: $owner_id}})"
            " SET d += $props RETURN d"
        )

        props: dict = {
            "title": document.title,
            "source": document.source.value,
            "schema_version": document.schema_version,
        }

        async with self._driver.session() as session:
            await session.run(
                query,
                identifier=identifier_value,
                owner_id=document.owner_id,
                props=props,
            )

    async def upsert_relations(self, relations: list[Relation]) -> None:
        """Crée ou met à jour les relations entre nœuds."""
        async with self._driver.session() as session:
            for relation in relations:
                source_identifier = relation.source_identifier.serialize()
                target_identifier = relation.target_identifier.serialize()

                query = (
                    "MATCH (a {identifier: $source_identifier, owner_id: $owner_id})"
                    " MATCH (b {identifier: $target_identifier, owner_id: $owner_id})"
                    " MERGE (a)-[r:REFERENCES {relation_type: $relation_type}]->(b)"
                    " SET r += $props RETURN r"
                )
                await session.run(
                    query,
                    source_identifier=source_identifier,
                    target_identifier=target_identifier,
                    owner_id=relation.owner_id,
                    relation_type=relation.relation_type.value,
                    props=dict(relation.metadata),
                )

    async def delete_relations_from(
        self, identifier: SourceIdentifier, owner_id: OwnerId, source: SourceName
    ) -> None:
        """Supprime uniquement les relations sortantes (préserve le nœud).
        
        Corrige le Bug 4 : utilise l'identifier correct pour matcher le nœud.
        """
        identifier_value = identifier.serialize()

        query = (
            "MATCH (d {identifier: $identifier, owner_id: $owner_id})-[r]->()"
            " DELETE r"
        )
        async with self._driver.session() as session:
            await session.run(
                query,
                identifier=identifier_value,
                owner_id=owner_id,
            )

    async def drop_all(self) -> None:
        """Detach-delete every node and relation. Irreversible — wipes all owners."""
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
