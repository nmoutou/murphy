"""Fabrique du client Mongo — une FONCTION, pas un singleton.

Un client mis en cache au niveau module serait rattaché à la boucle du premier
appelant. Tous les workers hériteraient de cette boucle-là : `_LOOP` reviendrait
par la porte de service, sous un autre nom. Chaque worker appelle donc la fabrique
depuis *son* runtime.
"""

from motor.motor_asyncio import AsyncIOMotorClient

__all__ = ["create_mongo_client"]


def create_mongo_client(uri: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(uri)
