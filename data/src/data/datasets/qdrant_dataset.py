"""Custom dataset for Qdrant connection and operations."""

import logging
from kedro.io import AbstractDataset
from typing import Any, Dict, Optional

class QdrantDataset(AbstractDataset):
    """Dataset encapsulant la connexion Qdrant.
    
    Expose le client via _load() / _get_client().
    L'exportation et le force-drop sont gérés par les nodes dédiés.
    
    Attributes:
        _connection_url: Qdrant server URL
        _api_key: Optional API key for authentication
        _collection_name: Target collection name
        _client: Qdrant client (created on first use)
    """
    
    def __init__(
        self,
        connection_url: str,
        collection: str,
        api_key: Optional[str] = None,
    ):
        """Initialize the Qdrant dataset.
        
        Args:
            connection_url: Qdrant server URL (ex: http://localhost:6333)
            collection: Name of the target collection
            api_key: Optional API key for authentication
        """
        self._connection_url = connection_url
        self._collection_name = collection
        self._api_key = api_key
        self._client = None
        self._log = logging.getLogger(__name__)
    
    def _get_client(self):
        """Get or create the Qdrant client connection.
        
        Returns:
            Qdrant client instance
        """
        if self._client is None:
            from qdrant_client import QdrantClient
            
            self._client = QdrantClient(url=self._connection_url, api_key=self._api_key)
        return self._client
    
    def _load(self):
        """Load the Qdrant client connection.
        
        Returns:
            Qdrant client instance
        """
        return self._get_client()
    
    def _describe(self) -> Dict[str, Any]:
        """Return dataset description.
        
        Returns:
            Dictionary containing dataset metadata
        """
        return {
            "connection_url": self._connection_url,
            "collection": self._collection_name,
            "type": "QdrantDataset",
        }
    
    def _save(self, data: Any) -> None:
        raise NotImplementedError("QdrantDataset is a read-only connection dataset.")
