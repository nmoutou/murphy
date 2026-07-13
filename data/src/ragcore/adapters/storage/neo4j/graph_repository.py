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
from ragcore.core.ports.graph_repository import RelationWriteResult

# Labels Neo4j connus, utilisés pour la création des index.
#
# `Unknown` en fait partie : c'est le nœud d'une cible DÉCRITE mais pas identifiée (la
# citation d'un arrêt : « Articles 1103 et 1229 du code civil »). Il n'est pas un
# second-rang — la passe de résolution devra l'énumérer et le matcher, et sans index elle
# scannerait le graphe entier à chaque run.
_KNOWN_LABELS = ("Document", "Article", "Texte", "Section", "Unknown")


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

    async def upsert_relations(self, relations: list[Relation]) -> RelationWriteResult:
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
            "MATCH (a {identifier: $source_identifier, owner_id: $owner_id})"
            " MATCH (b {identifier: $target_identifier, owner_id: $owner_id})"
            " MERGE (a)-[r:$($relation_type)]->(b)"
            " SET r += $props RETURN r"
        )

        # La cible DÉCRITE, elle, ne peut PAS être attendue : elle n'arrivera jamais.
        #
        # « Articles 1103 et 1229 du code civil » n'est pas un document du corpus — c'est
        # une phrase. Aucun run futur ne fera apparaître un nœud portant cet identifiant.
        # La traiter comme une pendante la condamnerait à l'être éternellement, et le
        # graphe de jurisprudence serait vide en attendant un événement impossible.
        #
        # On la CRÉE donc (`MERGE (b:Unknown)`), et c'est exactement la doctrine : « ce qui
        # n'est pas encore résolu n'est pas un état spécial — c'est un node unknown qui
        # attend sa passe de résolution ». Le nœud porte la phrase ; la citation existe
        # dans le graphe ; une passe ultérieure (extracteur de références + registre
        # d'alias) la résoudra en fusionnant ce nœud vers le vrai article — **sans
        # re-ingérer quoi que ce soit**, puisque le texte est déjà là.
        described = (
            "MATCH (a {identifier: $source_identifier, owner_id: $owner_id})"
            " MERGE (b:Unknown {identifier: $target_identifier, owner_id: $owner_id})"
            " SET b.text = $target_text"
            " MERGE (a)-[r:$($relation_type)]->(b)"
            " SET r += $props RETURN r"
        )

        async with self._driver.session() as session:
            for relation in relations:
                target = relation.target_identifier
                is_described = target.kind == "unknown"

                result = await session.run(
                    described if is_described else matched,
                    source_identifier=relation.source_identifier.serialize(),
                    target_identifier=target.serialize(),
                    target_text=target.raw,
                    owner_id=relation.owner_id,
                    relation_type=relation.relation_type,
                    props=dict(relation.metadata),
                )
                record = await result.single()
                if record is None:
                    pending.append(relation)
                else:
                    written.append(relation)

        return RelationWriteResult(written=written, pending=pending)

    async def existing_node_ids(
        self, identifiers: list[SourceIdentifier], owner_id: OwnerId
    ) -> set[str]:
        """Les identifiants (sérialisés) qui existent bel et bien comme nœuds."""
        if not identifiers:
            return set()

        query = (
            "MATCH (n) WHERE n.identifier IN $identifiers AND n.owner_id = $owner_id"
            " RETURN n.identifier AS identifier"
        )
        async with self._driver.session() as session:
            result = await session.run(
                query,
                identifiers=[i.serialize() for i in identifiers],
                owner_id=owner_id,
            )
            return {record["identifier"] async for record in result}

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
