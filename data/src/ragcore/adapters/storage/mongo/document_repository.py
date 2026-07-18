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
        # à faire en base. `structure["references"]` n'est plus persisté non plus :
        # les arêtes vivent dans Neo4j, et re-parser le XML est le coût assumé si la
        # table de traduction des verbes change. Le champ reste sur le MODÈLE (il
        # nourrit l'extracteur en phase 1, dans le même run) — il est retiré du DUMP.
        data = document.model_dump(mode="json", exclude={"source_files"})
        data["structure"].pop("references", None)
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
