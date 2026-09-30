from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.enums import SourceName
from ..models.identifiers import Identifier, OwnerId, RunId
from ..models.relation import Relation


@dataclass(frozen=True)
class RelationWriteResult:
    """Ce que l'écriture des arêtes a vraiment fait.

    Le ``None`` que retournait ``upsert_relations`` était le mensonge de comptage
    (§12) : ``RELATION_UPSERTED`` émettait ``count=len(relations)`` — le nombre de
    relations *tentées*. Une arête dont le ``MATCH (b)`` ne trouve rien n'est pas
    écrite, ne lève rien, et n'émettait rien : elle disparaissait en silence.

    Invariant : ``len(written) + len(pending) == len(relations en entrée)``.
    Aucune relation ne se perd entre l'entrée et la sortie — c'est *cela* qui rend
    §12 (comptage exact) et §13 (cache des pendantes) vérifiables.
    """

    written: list[Relation] = field(default_factory=list)
    pending: list[Relation] = field(default_factory=list)


@runtime_checkable
class GraphRepository(Protocol):
    """Stockage du graphe (Neo4j) — merge intelligent (pas de delete-node)."""

    async def merge_document_node(self, document: ParsedDocument) -> None: ...

    async def upsert_relations(
        self, relations: list[Relation], run_id: RunId
    ) -> RelationWriteResult:
        """Écrit les arêtes et RAPPORTE celles dont la cible n'existait pas.

        Une arête dont le ``MATCH (b)`` échoue n'est ni écrite, ni jetée : elle
        remonte dans ``.pending``. C'est l'appelant (ResolveRelationsService) qui
        décide de son sort — le repository, lui, ne connaît pas le cache §13.

        ``run_id`` **tague chaque arête écrite** (§8). Il n'est pas une propriété de la
        ``Relation`` — la même arête peut être (ré)écrite par des runs différents — mais
        du *geste d'écriture* : c'est lui qui rend la compensation par run possible
        (``delete_relations_by_run``). Sans lui, compenser un run reviendrait à supprimer
        TOUTES les arêtes sortantes d'un document, y compris celles qu'un autre run
        avait légitimement posées.
        """
        ...

    async def delete_relations_by_run(self, run_id: RunId, owner_id: OwnerId) -> None:
        """Supprime les arêtes écrites par CE run — et elles seules (§8).

        C'est la compensation à la maille du run : ``stratégie A`` (compensation
        systématique). Elle détache exactement ce que ``upsert_relations`` a tagué de ce
        ``run_id``, jamais plus. La sur-suppression que ``delete_relations_from`` risque
        (toutes les sortantes d'un nœud, quel qu'en soit l'auteur) est précisément ce que
        cette maille évite : un run rejoué ou annulé ne peut défaire que son propre
        ouvrage.
        """
        ...

    async def existing_node_ids(
        self, identifiers: list[Identifier], owner_id: OwnerId
    ) -> set[str]:
        """Sous-ensemble (sérialisé) des identifiants qui existent comme nœuds.

        Retourne des chaînes sérialisées : la comparaison avec les clés du cache
        (§13) se fait ainsi dans le même vocabulaire.

        Aucun chemin de production ne l'appelle encore (le §13 rejeu ciblé n'est pas
        câblé) : elle sert de point d'observation aux tests d'intégration Neo4j —
        contrat assumé vers v1, pas code mort.
        """
        ...

    async def delete_relations_from(
        self, identifier: Identifier, owner_id: OwnerId, source: SourceName
    ) -> None:
        """Supprime uniquement les relations sortantes (préserve les entrantes)."""
        ...

    async def compensate_document_node(
        self, identifier: Identifier, owner_id: OwnerId
    ) -> None:
        """Défait le nœud d'un document dont la saga a échoué — **sans casser le graphe**
        (§8, fin du ``_noop``).

        Le nœud n'est pas librement supprimable : d'AUTRES documents peuvent le citer
        (arêtes entrantes). Le supprimer emporterait leurs citations — une perte muette
        chez un tiers. La compensation est donc **conditionnelle** :

        - **aucune arête entrante** → le nœud n'existe que pour ce document raté :
          ``DETACH DELETE`` le retire entièrement ;
        - **au moins une arête entrante** → le nœud est une CIBLE citée : on ne le
          supprime pas, on le **dé-hydrate** en ``:Pending`` (il perd son contenu de
          document et redevient une cible ATTENDUE — un document identifié qui manque
          encore à l'appel, et qu'un run futur peut faire revenir).

        C'est ce qui remplace le ``_noop`` : le nœud orphelin ne survit plus à un échec,
        mais une cible citée n'est jamais arrachée au graphe d'autrui.
        """
        ...
