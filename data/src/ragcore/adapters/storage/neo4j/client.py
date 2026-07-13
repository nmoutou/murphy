"""Fabrique du driver Neo4j — une fonction, jamais un singleton (cf. mongo/client.py)."""

import neo4j

__all__ = ["create_neo4j_driver"]


def create_neo4j_driver(uri: str, username: str, password: str) -> neo4j.AsyncDriver:
    return neo4j.AsyncGraphDatabase.driver(uri, auth=(username, password))
