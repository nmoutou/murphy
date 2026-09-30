"""Implémentation Neo4j du GraphRepository.

Un nœud est identifié par son seul ``identifier`` sérialisé (p. ex.
``LEGIARTI000006419264``) — jamais par un champ deviné parmi plusieurs candidats : un
identifiant unique et explicite est ce qui rend le ``MERGE`` déterministe. Le label du
nœud vient de la table ``NodeLabels``, d'après les 8 lettres de l'identifiant.
"""

import neo4j

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier, OwnerId, RunId
from ragcore.core.models.relation import Relation
from ragcore.core.ports.graph_repository import RelationWriteResult

from .node_properties import PENDING_LABEL, NodeHydration, NodeLabels, node_props

__all__ = ["PENDING_LABEL", "Neo4jGraphRepository", "NodeHydration", "NodeLabels"]


_MERGE_NODE = (
    "MERGE (d {identifier: $identifier, owner_id: $owner_id})"
    " SET d:$($label)"
    # Le document est là : il n'est plus attendu. Neo4j ignore le retrait d'un label
    # absent, donc c'est sûr sur un nœud qui vient d'être créé.
    f" REMOVE d:{PENDING_LABEL}"
    " SET d += $props"
    " RETURN d"
)

_COUNT_INCOMING = (
    "MATCH (n {identifier: $identifier, owner_id: $owner_id})"
    " OPTIONAL MATCH (n)<-[incoming]-()"
    " RETURN count(incoming) AS entrantes"
)

_DETACH_DELETE_NODE = (
    "MATCH (n {identifier: $identifier, owner_id: $owner_id}) DETACH DELETE n"
)


def _dehydrate_node_query(labels: NodeLabels) -> str:
    """Ramène un nœud à l'état de cible attendue : ni label métier, ni props de document.

    `apoc.create.removeLabels` n'est pas garanti (pas d'APOC en prod) : on retire les
    labels connus par `REMOVE`. Neo4j ignore silencieusement le retrait d'un label absent
    — la liste couvre donc tous les labels métier sans avoir à savoir lequel ce nœud
    portait.
    """
    return (
        "MATCH (n {identifier: $identifier, owner_id: $owner_id})"
        f" REMOVE n:{':'.join(labels.known)}"
        f" SET n:{PENDING_LABEL}"
        " REMOVE n.title, n.source, n.schema_version, n.citations"
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
        self._dehydrate_node = _dehydrate_node_query(labels)
        # Défaut = régime prod (nœud maigre). Le hook passe l'hydratation de dev.
        self._hydration = hydration or NodeHydration()

    async def merge_document_node(self, document: ParsedDocument) -> None:
        """Merge un nœud document. Le label vient de ``NodeLabels``, d'après l'identifiant.

        **Le ``MERGE`` ne porte PAS le label — et c'est le point.** ``MERGE`` matche le
        motif ENTIER, label compris : ``MERGE (d:Article {identifier: X})`` ne retrouve
        pas un nœud du même identifiant portant un autre label, et en crée un SECOND. On
        ``MERGE`` donc sur le seul ``identifier``, ce qui retombe sur le nœud existant
        quel que soit son label, PUIS on pose le label réel.

        Les **citations** (cibles décrites) sont posées ici, en propriété du nœud, et non
        en arêtes vers des placeholders : voir ``node_properties.CITATIONS_PROP``.
        """
        async with self._driver.session() as session:
            await session.run(
                _MERGE_NODE,
                identifier=document.identifier.serialize(),
                owner_id=document.owner_id,
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
            "MATCH (a {identifier: $source_identifier, owner_id: $owner_id})"
            " MATCH (b {identifier: $target_identifier, owner_id: $owner_id})"
            " MERGE (a)-[r:$($relation_type)]->(b)"
            " SET r += $props SET r.run_id = $run_id, r.owner_id = $owner_id RETURN r"
        )

        # Il n'y a plus qu'un cas. Une cible DÉCRITE ne devient plus une arête vers un
        # placeholder : elle est un champ du document qui l'énonce (`citations`), posé au
        # `merge_document_node`. Toute relation qui arrive ici a donc une cible
        # identifiée, et le seul motif légitime est le `MATCH`.
        async with self._driver.session() as session:
            for relation in relations:
                result = await session.run(
                    matched,
                    source_identifier=relation.source_identifier.serialize(),
                    target_identifier=relation.target_identifier.serialize(),
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
        self, identifiers: list[Identifier], owner_id: OwnerId
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
        self, identifier: Identifier, owner_id: OwnerId, source: SourceName
    ) -> None:
        """Supprime les seules relations SORTANTES du nœud, sans toucher au nœud.

        Le ``MATCH`` porte sur l'``identifier`` sérialisé — la même clé que ``merge``, donc
        on retrouve exactement le nœud écrit. Ne supprimer que le sortant préserve les
        arêtes qu'un AUTRE document a posées vers celui-ci.
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
        self, identifier: Identifier, owner_id: OwnerId
    ) -> None:
        """Défait le nœud d'un document raté sans arracher les citations d'autrui (§8).

        Conditionnel sur l'existence d'une arête ENTRANTE :

        - aucune entrante → ``DETACH DELETE`` : le nœud n'existait que pour ce document ;
        - au moins une entrante → **dé-hydratation** : le nœud est cité, on ne le
          supprime pas. On lui retire ses labels métier et ses propriétés de document
          pour le ramener au statut de cible ATTENDUE (``:Pending``). La référence
          entrante survit ; le contenu du document raté, non.

        **Lire le nombre d'entrantes, puis brancher** — deux requêtes, pas une acrobatie
        Cypher mêlant ``DETACH DELETE`` et ``REMOVE`` sous condition dans la même passe
        (fragile, et interdite d'APOC en prod). La fenêtre entre la lecture et l'écriture
        n'est pas un risque ici : la compensation survient dans la saga d'UN document, et
        l'invariant 2 du §11 (dispatch par clé) garantit qu'un seul worker touche ce nœud
        à la fois — personne n'ajoute d'entrante en parallèle sur cet identifiant.

        La ré-hydratation d'un ``:Pending`` vers un vrai document, quand le document
        revient, est déjà le comportement de ``merge_document_node`` (le ``MERGE`` sur
        ``identifier`` retombe sur le même nœud et réécrit ses props) : dé-hydrater n'est
        donc pas une impasse, c'est un retour à l'état « cible en attente ».
        """
        identifier_value = identifier.serialize()
        async with self._driver.session() as session:
            result = await session.run(
                _COUNT_INCOMING, identifier=identifier_value, owner_id=owner_id
            )
            record = await result.single()
            # Le nœud n'existe pas (la saga a échoué AVANT le merge du nœud) : rien à
            # défaire. La compensation est idempotente — c'est ce que la saga attend.
            if record is None:
                return
            query = (
                _DETACH_DELETE_NODE
                if record["entrantes"] == 0
                else self._dehydrate_node
            )
            await session.run(query, identifier=identifier_value, owner_id=owner_id)

    async def drop_all(self) -> None:
        """Detach-delete every node and relation. Irreversible — wipes all owners."""
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
