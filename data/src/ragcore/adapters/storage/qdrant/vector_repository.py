"""Implémentation Qdrant du VectorRepository.

Changements post-refonte :
- Hash stable : hashlib.sha256 au lieu de hash() Python (corrige Bug 6)
- Payload : "identifier" au lieu de "document_id"
- Filtre : match sur "identifier" au lieu de "document_id"
"""

import hashlib

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ragcore.core.models.chunk import EmbeddedChunk
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

    async def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        if not await self._client.collection_exists(self._collection_name):
            await self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )

    async def upsert(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        """Upsert embedded chunks into Qdrant."""
        if not embedded_chunks:
            return
        await self._ensure_collection()
        points = [
            PointStruct(
                id=self._stable_hash_id(ec.chunk.chunk_id),
                vector=ec.embedding,
                payload={
                    "chunk_id": ec.chunk.chunk_id,
                    "identifier": ec.chunk.parent_identifier.serialize(),
                    "owner_id": ec.chunk.owner_id,
                    **ec.chunk.metadata,
                },
            )
            for ec in embedded_chunks
        ]
        await self._client.upsert(collection_name=self._collection_name, points=points)

    @staticmethod
    def _stable_hash_id(chunk_id: str) -> int:
        """Génère un ID Qdrant stable depuis un chunk_id via SHA-256.
        
        Corrige Bug 6 : remplace abs(hash()) qui n'est pas stable entre processus.
        """
        digest = hashlib.sha256(chunk_id.encode()).hexdigest()
        return int(digest, 16) % (2**63)

    async def delete_by_document(self, identifier: SourceIdentifier, owner_id: OwnerId) -> None:
        """Delete all vectors belonging to a given document for a given owner."""
        await self._ensure_collection()
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
