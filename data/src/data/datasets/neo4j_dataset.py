"""Custom dataset for Neo4j connection and operations."""

from kedro.io import AbstractDataset
from typing import Any, Dict, Optional
from neo4j import GraphDatabase
from neo4j import Driver as Neo4jDriver


class Neo4jDataset(AbstractDataset):
    """Dataset encapsulant la connexion Neo4j.
    
    Expose le driver via _load() / _get_driver().
    L'exportation et le force-drop sont gérés par les nodes dédiés.
    
    Attributes:
        _connection_uri: URI de connexion Bolt Neo4j
        _auth: Tuple (username, password) pour l'authentification
        _driver: Driver Neo4j (créé lors de la première utilisation)
    """
    
    def __init__(
        self,
        connection_uri: str,
        auth: Optional[dict] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ):
        """Initialise le dataset Neo4j.
        
        Args:
            connection_uri: URI de connexion Bolt (ex: bolt://localhost:7687)
            auth: Authentification sous forme de dict {"username": ..., "password": ...}
            credentials: Dictionnaire de credentials injecté par Kedro
        """
        self._connection_uri = connection_uri
        if credentials and auth is None:
            auth = credentials.get("auth")
        try:
            self._auth = (auth["username"], auth["password"])
        except (KeyError, TypeError) as e:
            raise ValueError(
                f"auth must be a dict with 'username' and 'password' keys, got: {auth!r}"
            ) from e
        self._driver: Optional[Neo4jDriver] = None
    
    def _get_driver(self) -> Neo4jDriver:
        """Obtient ou crée le driver Neo4j.
        
        Returns:
            Driver Neo4j
        """
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._connection_uri,
                auth=self._auth
            )
        return self._driver
    
    def _load(self) -> Neo4jDriver:
        """Charge le driver Neo4j.
        
        Returns:
            Driver Neo4j
        """
        return self._get_driver()
    
    def _describe(self) -> Dict[str, Any]:
        """Retourne une description du dataset.
        
        Returns:
            Dictionnaire contenant les métadonnées du dataset
        """
        return {
            "connection_uri": self._connection_uri,
            "auth": f"{self._auth[0]}/***",
            "type": "Neo4jDataset",
        }
    
    def _save(self, data: Any) -> None:
        raise NotImplementedError("Neo4JDataset is a read-only connection dataset.")
