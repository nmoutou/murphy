"""Une fonction, jamais un singleton (cf. mongo/client.py)."""

from opensearchpy import AsyncOpenSearch

__all__ = ["create_opensearch_client"]


def create_opensearch_client(url: str) -> AsyncOpenSearch:
    """Aucune relance : un échec arrête le document, et la saga compense."""
    return AsyncOpenSearch(hosts=[url], max_retries=0)
