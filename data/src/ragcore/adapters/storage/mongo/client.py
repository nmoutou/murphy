"""Fabrique du client Mongo : une fonction, pas un singleton, car un client est lié à
la boucle qui le crée. Chaque worker l'appelle depuis son runtime.
"""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

MongoClient = AsyncIOMotorClient[dict[str, Any]]
MongoDatabase = AsyncIOMotorDatabase[dict[str, Any]]

__all__ = ["MongoClient", "MongoDatabase", "create_mongo_client"]


def create_mongo_client(uri: str) -> MongoClient:
    return AsyncIOMotorClient(uri)
