"""Une fonction, jamais un singleton (cf. mongo/client.py)."""

from qdrant_client import AsyncQdrantClient

__all__ = ["create_qdrant_client"]


def create_qdrant_client(url: str, api_key: str | None = None) -> AsyncQdrantClient:
    return AsyncQdrantClient(url=url, api_key=api_key)
