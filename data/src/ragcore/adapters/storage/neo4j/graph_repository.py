"""Implémentation Neo4j du GraphRepository.

Changements post-refonte :
- Identifiant unique : `identifier` (value=kind:raw, ex."eli:LEGIARTI...")
- Suppression de `source_id_fields` et des fallbacks dangereux (Bugs 2-3)
- Label dérivé du document.identifier.document_type
"""

from typing import Any

import neo4j

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId, SourceIdentifier
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
                    f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.identifier)"
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

        props: dict[str, Any] = {
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
            "MATCH (a {identifier: $source_identifier, owner_id: $owner_id})"
            " MATCH (b {identifier: $target_identifier, owner_id: $owner_id})"
            " MERGE (a)-[r:$($relation_type)]->(b)"
            " SET r += $props SET r.run_id = $run_id, r.owner_id = $owner_id RETURN r"
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
            " SET r += $props SET r.run_id = $run_id, r.owner_id = $owner_id RETURN r"
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
                    run_id=run_id,
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
            "MATCH (d {identifier: $identifier, owner_id: $owner_id})-[r]->() DELETE r"
        )
        async with self._driver.session() as session:
            await session.run(
                query,
                identifier=identifier_value,
                owner_id=owner_id,
            )

    async def delete_relations_by_run(self, run_id: RunId, owner_id: OwnerId) -> None:
        """Détache les arêtes taguées de ce ``run_id`` — et elles seules (§8).

        La maille de compensation. ``upsert_relations`` pose ``r.run_id`` sur chaque
        arête écrite ; ici on ne défait QUE celles-là. La différence avec
        ``delete_relations_from`` est le cœur du §8 : cette dernière supprime *toutes*
        les sortantes d'un nœud, quel qu'en soit l'auteur — un run rejoué emporterait les
        arêtes qu'un autre run avait posées. Filtrer sur ``run_id`` borne la suppression
        à l'ouvrage du run, exactement.

        ``owner_id`` reste une composante de la sélection : deux tenants n'ont aucune
        raison de partager un ``run_id``, mais un filtre qui l'ignore serait la première
        exception à l'invariant « ``owner_id`` est partout une clé ».
        """
        query = (
            "MATCH ()-[r]->() WHERE r.run_id = $run_id AND r.owner_id = $owner_id"
            " DELETE r"
        )
        async with self._driver.session() as session:
            await session.run(query, run_id=run_id, owner_id=owner_id)

    async def compensate_document_node(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> None:
        """Défait le nœud d'un document raté sans arracher les citations d'autrui (§8).

        Conditionnel sur l'existence d'une arête ENTRANTE :

        - aucune entrante → ``DETACH DELETE`` : le nœud n'existait que pour ce document ;
        - au moins une entrante → **dé-hydratation** : le nœud est cité, on ne le
          supprime pas. On lui retire ses labels métier et ses propriétés de document
          pour le ramener au statut de cible décrite (``:Unknown``), celui-là même qu'une
          citation non résolue produit. La citation entrante survit ; le contenu du
          document raté, non.

        **Lire le nombre d'entrantes, puis brancher** — deux requêtes, pas une acrobatie
        Cypher mêlant ``DETACH DELETE`` et ``REMOVE`` sous condition dans la même passe
        (fragile, et interdite d'APOC en prod). La fenêtre entre la lecture et l'écriture
        n'est pas un risque ici : la compensation survient dans la saga d'UN document, et
        l'invariant 2 du §11 (dispatch par clé) garantit qu'un seul worker touche ce nœud
        à la fois — personne n'ajoute d'entrante en parallèle sur cet identifiant.

        La ré-hydratation d'un ``:Unknown`` vers un vrai document, quand le document
        revient, est déjà le comportement de ``merge_document_node`` (le ``MERGE`` sur
        ``identifier`` retombe sur le même nœud et réécrit ses props) : dé-hydrater n'est
        donc pas une impasse, c'est un retour à l'état « cible en attente ».
        """
        identifier_value = identifier.serialize()
        async with self._driver.session() as session:
            record = await (
                await session.run(
                    "MATCH (n {identifier: $identifier, owner_id: $owner_id})"
                    " OPTIONAL MATCH (n)<-[incoming]-()"
                    " RETURN count(incoming) AS entrantes",
                    identifier=identifier_value,
                    owner_id=owner_id,
                )
            ).single()

            # Le nœud n'existe pas (la saga a échoué AVANT le merge du nœud) : rien à
            # défaire. La compensation est idempotente — c'est ce que la saga attend.
            if record is None:
                return

            if record["entrantes"] == 0:
                await session.run(
                    "MATCH (n {identifier: $identifier, owner_id: $owner_id})"
                    " DETACH DELETE n",
                    identifier=identifier_value,
                    owner_id=owner_id,
                )
                return

            # `apoc.create.removeLabels` n'est pas garanti (pas d'APOC en prod) : on
            # retire les labels connus par `REMOVE`. Neo4j ignore silencieusement le
            # retrait d'un label absent — la liste couvre donc tous les labels métier
            # sans avoir à savoir lequel ce nœud portait.
            removable = ":".join(label for label in _KNOWN_LABELS if label != "Unknown")
            await session.run(
                "MATCH (n {identifier: $identifier, owner_id: $owner_id})"
                f" REMOVE n:{removable}"
                " SET n:Unknown"
                " SET n.text = coalesce(n.title, n.identifier)"
                " REMOVE n.title, n.source, n.schema_version",
                identifier=identifier_value,
                owner_id=owner_id,
            )

    async def drop_all(self) -> None:
        """Detach-delete every node and relation. Irreversible — wipes all owners."""
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
