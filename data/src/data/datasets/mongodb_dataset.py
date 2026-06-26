"""Custom dataset for MongoDB connection and operations."""

from kedro.io import AbstractDataset
from typing import Any, Dict, Optional
from pymongo import MongoClient
from pymongo.database import Database


class MongoDBDataset(AbstractDataset):
    """Dataset encapsulant la connexion MongoDB.
    
    Expose la database via _load() / _get_database().
    L'exportation et le force-drop sont gérés par les nodes dédiés.
    
    Attributes:
        _connection_uri: URI de connexion MongoDB
        _database_name: Nom de la base de données
        _client: Client MongoDB (créé lors de la première utilisation)
        _database: Database MongoDB (créé lors de la première utilisation)
    """
    
    def __init__(
        self,
        database: str,
        connection_uri: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ):
        """Initialise le dataset MongoDB.
        
        Args:
            database: Nom de la base de données
            connection_uri: URI de connexion MongoDB (ex: mongodb://admin:admin@localhost:27017/)
            credentials: Dictionnaire de credentials injecté par Kedro
        """
        if credentials:
            connection_uri = credentials.get("connection_uri", connection_uri)
        if not connection_uri:
            raise ValueError("connection_uri must be provided either directly or via credentials")
        self._connection_uri = connection_uri
        self._database_name = database
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None
    
    def _get_database(self) -> Database:
        """Obtient ou crée la connexion à la base de données.
        
        Returns:
            Database MongoDB
        """
        if self._database is None:
            if self._client is None:
                self._client = MongoClient(self._connection_uri)
            self._database = self._client[self._database_name]
        return self._database
    
    def _load(self) -> Database:
        """Charge la connexion à la base de données.
        
        Returns:
            Database MongoDB
        """
        return self._get_database()
    
    def _describe(self) -> Dict[str, Any]:
        """Retourne une description du dataset.
        
        Returns:
            Dictionnaire contenant les métadonnées du dataset
        """
        return {
            "connection_uri": self._connection_uri,
            "database": self._database_name,
            "type": "MongoDBDataset",
        }

    def _save(self, data: Any) -> None:
        raise NotImplementedError("MongoDBDataset is a read-only connection dataset.")


