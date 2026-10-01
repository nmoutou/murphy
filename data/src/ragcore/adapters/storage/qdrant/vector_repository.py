"""Implémentation Qdrant du VectorRepository."""

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
from ragcore.core.models.identifiers import Identifier


class QdrantVectorRepository:
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
        """À appeler une seule fois, avant le pool : depuis les workers, ce
        check-then-act ferait échouer en `409 Conflict` tous les créateurs sauf un.
        """
        if not await self._client.collection_exists(self._collection_name):
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size, distance=Distance.COSINE
                ),
            )

    async def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> None:
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
        """Les champs du contrat de service (ADR-039) viennent en dernier : une
        métadonnée homonyme ne peut pas les écraser. Le texte du passage n'y est pas : il
        se lit dans le ``content`` du document Mongo.
        """
        return {
            **chunk.metadata,
            "chunk_id": chunk.chunk_id,
            "identifier": chunk.parent_identifier.serialize(),
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "document_type": chunk.document_type.value,
            "nature": chunk.nature,
        }

    @staticmethod
    def _stable_hash_id(chunk_id: str) -> int:
        """SHA-256 plutôt que ``hash()``, resemé par interpréteur : un run qui réécrit un
        chunk doit retomber sur le même ID."""
        digest = hashlib.sha256(chunk_id.encode()).hexdigest()
        return int(digest, 16) % (2**63)

    async def delete_by_document(self, identifier: Identifier) -> None:
        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="identifier",
                        match=MatchValue(value=identifier.serialize()),
                    ),
                ]
            ),
        )

    async def drop_all_collections(self) -> None:
        """Irréversible. Toutes les collections, pas seulement celle du run : une
        collection créée sous un autre nom traînerait sinon sur le disque.
        """
        collections = await self._client.get_collections()
        for descriptor in collections.collections:
            await self._client.delete_collection(collection_name=descriptor.name)
