"""Le payload Qdrant est un contrat : le serving y lit les champs d'ADR-039.

Un faux client suffit ici : ce qui compte est ce que le dépôt CONSTRUIT, pas ce que
Qdrant en fait (les filtres, eux, sont testés contre la vraie base en intégration).
"""

from typing import Any

from qdrant_client.models import PointStruct

from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.enums import DocumentType
from ragcore.core.models.identifiers import Identifier

DIM = 4


class CapturingQdrantClient:
    """Retient les points qu'on lui envoie."""

    def __init__(self) -> None:
        self.points: list[PointStruct] = []

    async def upsert(self, collection_name: str, points: list[PointStruct]) -> None:
        self.points.extend(points)


def _embedded(metadata: dict[str, Any]) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk=Chunk(
            chunk_id="LEGIARTI000033972545_0001",
            parent_identifier=Identifier(raw="LEGIARTI000033972545"),
            document_type=DocumentType.ARTICLE,
            ordinal=1,
            text="passage",
            tag_path=[],
            char_start=359,
            char_end=742,
            metadata=metadata,
        ),
        embedding=[0.1] * DIM,
        embedding_model="test",
        embedding_dim=DIM,
    )


async def _payload_of(chunk: EmbeddedChunk) -> dict[str, Any]:
    client = CapturingQdrantClient()
    repo = QdrantVectorRepository(client, "chunks_test", DIM)  # type: ignore[arg-type]  # faux client

    await repo.upsert([chunk])

    payload = client.points[0].payload
    assert payload is not None
    return payload


async def test_the_payload_carries_the_serving_contract() -> None:
    payload = await _payload_of(_embedded({"num": "L. 110-1"}))

    assert payload["chunk_id"] == "LEGIARTI000033972545_0001"
    assert payload["identifier"] == Identifier(raw="LEGIARTI000033972545").serialize()
    assert payload["char_start"] == 359
    assert payload["char_end"] == 742
    assert payload["document_type"] == "article"
    assert payload["nature"] is None
    assert payload["num"] == "L. 110-1", "les autres métadonnées restent à plat"


async def test_a_metadata_key_can_NOT_overwrite_a_contract_field() -> None:
    """Une métadonnée homonyme écraserait l'offset en silence."""
    payload = await _payload_of(
        _embedded({"char_start": 0, "identifier": "faux", "document_type": "faux"})
    )

    assert payload["char_start"] == 359
    assert payload["document_type"] == "article"
    assert payload["identifier"] == Identifier(raw="LEGIARTI000033972545").serialize()
