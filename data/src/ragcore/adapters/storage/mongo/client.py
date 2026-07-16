"""Fabrique du client Mongo — une FONCTION, pas un singleton.

Un client mis en cache au niveau module serait rattaché à la boucle du premier
appelant. Tous les workers hériteraient de cette boucle-là : `_LOOP` reviendrait
par la porte de service, sous un autre nom. Chaque worker appelle donc la fabrique
depuis *son* runtime.
"""

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Motor paramètre ses classes par le type du document BSON. Nos documents sont des
# dicts JSON-compatibles : on nomme le type une fois ici plutôt que de répéter
# `dict[str, Any]` dans chaque repo.
MongoClient = AsyncIOMotorClient[dict[str, Any]]
MongoDatabase = AsyncIOMotorDatabase[dict[str, Any]]

__all__ = ["MongoClient", "MongoDatabase", "create_mongo_client"]


def create_mongo_client(uri: str) -> MongoClient:
    return AsyncIOMotorClient(uri)
