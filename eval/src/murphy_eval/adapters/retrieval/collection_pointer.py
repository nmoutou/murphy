"""Découverte de la collection Qdrant à interroger — via le pointeur Mongo.

Une ingestion qui finit ``ok`` publie le nom de sa collection dans
``MURPHY_META.meta_published_collection``, doc ``{key: "current"}``, champ
``collection_name`` (``ragcore`` :
``adapters/storage/mongo/published_collection_repository``). Le backend lit
exactement ce pointeur au boot (``backend/src/infra/collectionPointer.ts``) ; le
harnais fait de même — **même source de vérité que la prod**, jamais un nom en
dur.

**Couture B-13.** L'orchestrateur de sweep recalculera le fingerprint blake2b de
``W`` (``ragcore/core/config/fingerprint.py`` : ``canonicalize`` =
``json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True)`` puis
``blake2b(digest_size=16)``) et le comparera à ce ``collection_name`` (fail-fast
sur divergence). B-05 se contente de **lire** le pointeur ; il ne vérifie pas
encore la cohérence ``W ↔ collection`` — c'est le rôle de B-13.
"""

from __future__ import annotations

from pymongo import MongoClient

POINTER_COLLECTION = "meta_published_collection"
POINTER_KEY = "current"


def read_published_collection(mongo_uri: str, meta_db_name: str) -> str:
    """Renvoie le ``collection_name`` publié par la dernière ingestion ``ok``.

    Fail-fast si aucun pointeur n'existe : sans ingestion publiée, le harnais
    n'a rien à interroger, et deviner un nom serait pire que s'arrêter.
    """
    client: MongoClient[dict[str, object]] = MongoClient(mongo_uri)
    try:
        document = client[meta_db_name][POINTER_COLLECTION].find_one(
            {"key": POINTER_KEY}
        )
    finally:
        client.close()
    if document is None:
        raise RuntimeError(
            f"Aucun pointeur de collection publié dans "
            f"{meta_db_name}.{POINTER_COLLECTION} (key={POINTER_KEY!r}). "
            f"Une ingestion 'ok' doit d'abord publier avant d'évaluer."
        )
    collection_name = document.get("collection_name")
    if not isinstance(collection_name, str) or not collection_name:
        raise RuntimeError(
            f"Pointeur présent mais 'collection_name' absent ou invalide : "
            f"{collection_name!r}."
        )
    return collection_name
