"""Implémentation MongoDB du DocumentRepository.

L'``upsert`` remplace le document **en place et atomiquement** (``replace_one`` avec
``upsert=True``). Le remplacement d'une version existante n'a jamais d'instant à vide :
là où un ``delete`` suivi d'un ``insert`` exposait une fenêtre où l'identifiant
n'existait plus, ``replace_one`` échange ancien→neuf en une seule opération indivisible,
ou crée le document s'il est absent. La saga n'a donc rien à détruire avant d'écrire.
"""

from ragcore.adapters.storage.mongo.client import MongoClient, MongoDatabase
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import OwnerId, SourceIdentifier


def _serialize_identifier(identifier: SourceIdentifier) -> str:
    """Sérialise un identifier pour la persistance."""
    return identifier.serialize()


class MongoDocumentRepository:
    """MongoDB implementation of DocumentRepository (atomic replace upsert)."""

    def __init__(
        self,
        client: MongoClient,
        db_name: str,
        collection: str = "documents",
    ) -> None:
        self._database = client[db_name]
        self._collection = self._database[collection]

    @property
    def database(self) -> MongoDatabase:
        """La DB qui porte la collection — de quoi reposer les index après un drop."""
        return self._database

    async def upsert(self, document: ParsedDocument) -> None:
        """Remplace le document en place (atomique), ou le crée s'il est absent.

        ``replace_one(..., upsert=True)`` sur la clé ``(identifier, owner_id)`` : un seul
        aller-retour indivisible. Aucun instant où l'identifiant n'existe plus — c'est ce
        qui retire à la saga tout besoin de détruire l'ancien avant d'écrire le neuf.
        """
        identifier_key = _serialize_identifier(document.identifier)
        filter_ = {
            "identifier": identifier_key,
            "owner_id": document.owner_id,
        }
        # Épuration (ADR-022 §4) : `source_files` est de la provenance d'inspection
        # (Neo4j dev), pas du contenu — un chemin absolu du poste d'ingestion n'a rien
        # à faire en base. `structure` NE L'EST PLUS DU TOUT, ses trois clés étant
        # chacune redondante avec ce qui est déjà persisté ailleurs :
        #
        # - `references` et `context` sont de la donnée d'ARÊTE : elles vivent dans
        #   Neo4j. Re-parser le XML est le coût assumé si la table de traduction des
        #   verbes change.
        # - `sections` est `content` re-découpé : `_content` et `_sections` lisent les
        #   MÊMES blocs, dans le même ordre (generic/parser.py), donc le texte y était
        #   stocké deux fois. Son seul apport propre, le `path`, survit sur les chunks
        #   (`tag_path`), avec en prime les offsets (`char_start`/`char_end`) que
        #   `sections` ne portait même pas. Un bloc n'ayant produit AUCUN chunk perd sa
        #   trace d'arborescence en Mongo — cas accepté : le graphe porte la contenance.
        #
        # Les trois champs restent sur le MODÈLE (le chunker et l'extracteur les lisent
        # en phase 1, dans le même run, en mémoire) — ils sont retirés du DUMP.
        data = document.model_dump(mode="json", exclude={"source_files", "structure"})
        # Le champ sérialisé porte l'indexation ; il double la clé du filtre.
        data["identifier"] = identifier_key
        await self._collection.replace_one(filter_, data, upsert=True)

    async def delete(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None:
        await self._collection.delete_many(
            {
                "identifier": _serialize_identifier(identifier),
                "owner_id": owner_id,
            }
        )

    async def drop_collection(self) -> None:
        """Drop the entire collection. Irreversible — wipes all owners."""
        await self._collection.drop()
