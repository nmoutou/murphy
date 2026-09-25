"""Implémentation Qdrant du VectorRepository.

L'ID d'un point dérive du ``chunk_id`` par SHA-256 — un hash **stable entre processus**,
là où le ``hash()`` de Python est resemé à chaque interpréteur : deux runs auraient sinon
écrit le même chunk sous deux ID différents, et l'un n'aurait jamais écrasé l'autre. Le
document est nommé partout (payload comme filtre) par son ``identifier`` sérialisé, la même
clé qu'en Mongo et Neo4j.
"""

import hashlib
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.identifiers import OwnerId, SourceIdentifier


class QdrantVectorRepository:
    """Qdrant implementation of VectorRepository (delete-then-insert via upsert)."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self._client = client
        self._collection_name = collection_name
        self._vector_size = vector_size

    async def ensure_collection(self) -> None:
        """Crée la collection si elle n'existe pas. **Setup partagé : à appeler une
        seule fois, avant le pool de workers.**

        Ce `collection_exists` puis `create_collection` est un check-then-act. Appelé
        depuis les workers, il produit une course : N workers constatent l'absence de
        la collection, tous la créent, et Qdrant renvoie `409 Conflict` à tous sauf
        un — que la saga traite alors comme un échec métier et compense, perdant le
        document. La course ne se rattrape pas, elle s'évite : la collection est un
        setup de run, pas un travail par document.
        """
        if not await self._client.collection_exists(self._collection_name):
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size, distance=Distance.COSINE
                ),
            )

    async def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        """Upsert embedded chunks into Qdrant."""
        if not embedded_chunks:
            return
        points = [
            PointStruct(
                id=self._stable_hash_id(ec.chunk.chunk_id),
                vector=ec.embedding,
                payload=self._payload(ec.chunk),
            )
            for ec in embedded_chunks
        ]
        await self._client.upsert(collection_name=self._collection_name, points=points)

    @staticmethod
    def _payload(chunk: Chunk) -> dict[str, Any]:
        """Le payload d'un point : les métadonnées à plat, PUIS les champs du contrat.

        Les champs que le serving lit (ADR-039, contrat v1) viennent en dernier : une
        métadonnée homonyme ne peut pas les écraser. Le texte du passage n'y est pas —
        il vit dans le ``content`` du document Mongo, entre ``char_start`` et
        ``char_end`` (points de code).
        """
        return {
            **chunk.metadata,
            "chunk_id": chunk.chunk_id,
            "identifier": chunk.parent_identifier.serialize(),
            "owner_id": chunk.owner_id,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
        }

    @staticmethod
    def _stable_hash_id(chunk_id: str) -> int:
        """Un ID Qdrant STABLE dérivé du chunk_id par SHA-256.

        « Stable » est le mot qui compte : le même chunk_id donne le même ID à tous les
        runs et tous les processus. ``hash()`` de Python ne le garantit pas (il est resemé
        par interpréteur) — le réemployer aurait dispersé un même chunk sur plusieurs ID.
        """
        digest = hashlib.sha256(chunk_id.encode()).hexdigest()
        return int(digest, 16) % (2**63)

    async def delete_by_document(
        self, identifier: SourceIdentifier, owner_id: OwnerId
    ) -> None:
        """Delete all vectors belonging to a given document for a given owner."""
        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="identifier",
                        match=MatchValue(value=identifier.serialize()),
                    ),
                    FieldCondition(
                        key="owner_id",
                        match=MatchValue(value=owner_id),
                    ),
                ]
            ),
        )

    async def drop_collection(self) -> None:
        """Drop the entire Qdrant collection. Irreversible — wipes all owners.

        No-op if the collection does not exist.
        """
        if await self._client.collection_exists(self._collection_name):
            await self._client.delete_collection(collection_name=self._collection_name)

    async def drop_all_collections(self) -> None:
        """Drop EVERY collection of the Qdrant store. Irreversible.

        Contrairement à ``drop_collection`` (scopé à la collection dérivée du
        fingerprint courant), ceci vide le store entier : les collections des
        stratégies d'embedding abandonnées — un autre ``chunk_size``, un autre
        modèle — traînent sinon sur le disque sans que le fingerprint courant les
        connaisse. C'est le levier disque du mode ``nuke_all``. À ne jamais appeler
        hors d'un environnement jetable.
        """
        collections = await self._client.get_collections()
        for descriptor in collections.collections:
            await self._client.delete_collection(collection_name=descriptor.name)
