"""Test d'intégration : le vrai chemin de lecture Qdrant de l'adapter baseline.

On peuple un Qdrant éphémère (testcontainers) avec des points au **format de
payload exact de l'ingestion** (``{chunk_id, identifier, owner_id, ...}``, cf.
``ragcore/adapters/storage/qdrant/vector_repository.py``), puis on vérifie que
``QdrantSearchClient`` les retrouve et remonte ``identifier`` comme ``doc_id``,
triés par similarité. C'est la preuve que la couture ADR-018 tient contre un
vrai serveur, pas seulement en fonction pure.

Hors CI par défaut (marker ``integration``, nécessite Docker).
"""

from __future__ import annotations

import pytest

qdrant_container = pytest.importorskip("testcontainers.qdrant")
qdrant_models = pytest.importorskip("qdrant_client.models")

from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.models import Distance, PointStruct, VectorParams  # noqa: E402
from testcontainers.qdrant import QdrantContainer  # noqa: E402

from murphy_eval.adapters.retrieval import qdrant_search  # noqa: E402

QdrantSearchClient = qdrant_search.QdrantSearchClient

_DIM = 4
_COLLECTION = "test_chunks"


@pytest.mark.integration
def test_search_remonte_identifier_comme_doc_id_trie_par_score() -> None:
    with QdrantContainer("qdrant/qdrant:v1.15.1") as container:
        url = f"http://{container.rest_host_address}"

        admin = QdrantClient(url=url)
        admin.create_collection(
            collection_name=_COLLECTION,
            vectors_config=VectorParams(size=_DIM, distance=Distance.COSINE),
        )
        admin.upsert(
            collection_name=_COLLECTION,
            points=[
                PointStruct(
                    id=1,
                    vector=[1.0, 0.0, 0.0, 0.0],
                    payload={
                        "chunk_id": "chunk-a",
                        "identifier": "eli:LEGIARTI000000000001",
                        "owner_id": "system",
                    },
                ),
                PointStruct(
                    id=2,
                    vector=[0.0, 1.0, 0.0, 0.0],
                    payload={
                        "chunk_id": "chunk-b",
                        "identifier": "decision:JURITEXT000000000002",
                        "owner_id": "system",
                    },
                ),
            ],
        )
        admin.close()

        client = QdrantSearchClient(url=url, collection_name=_COLLECTION)
        try:
            hits = client.search([1.0, 0.0, 0.0, 0.0], top_k=2)
        finally:
            client.close()

        assert hits[0].chunk_id == "chunk-a"
        assert hits[0].identifier == "eli:LEGIARTI000000000001"
        assert hits[0].score >= hits[1].score
        assert {h.identifier for h in hits} == {
            "eli:LEGIARTI000000000001",
            "decision:JURITEXT000000000002",
        }
