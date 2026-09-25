"""``fingerprint()`` — config canonicalisée → hash. Une fonction pure, et un engagement.

**Ce qu'elle nomme.** La collection Qdrant (§6) et le run MLflow (§9) portent le même
hash. C'est ce qui rend l'A/B lisible : deux stratégies d'embedding produisent deux
collections qui coexistent, chacune rejouable, et le run MLflow qui porte les
paramètres *en clair* lève l'opacité du hash.

**Pourquoi un hash pur, et pas un nom lisible.** Un nom composé (``mpnet_768_c128``)
est fragile : il faut décider comment abréger chaque nouveau paramètre, et deux
configs distinctes finissent par se retrouver avec le même nom. Le hash absorbe
n'importe quel paramètre sans qu'on ait à y réfléchir, et ne collisionne pas.
L'opacité est **assumée** — elle est levée par le tracking, pas par le nom.

**L'engagement, et c'est pourquoi il y a un golden.** Même config → même hash, *pour
toujours*. Si la canonicalisation bouge, tous les noms de collection bougent : les
vecteurs déjà écrits deviennent orphelins et le prochain run les réécrit ailleurs, en
silence. Le cliquet ``golden/test_fingerprint.py`` fige des hashs littéraux — les
changer est un geste visible en revue, ce qui est précisément l'effet recherché.

**La garantie structurelle.** La signature ne prend qu'un ``WorkflowConfig``. Elle n'a
donc *physiquement* pas accès à l'URI Mongo, au mot de passe Neo4j ni au chemin des
sources : ils ne sont pas dans le type. L'erreur « j'ai hashé une URI et fragmenté mes
collections en déménageant la base » n'est pas *évitée par convention* — elle est
**impossible**. C'est la forme d'argument que le principe directeur d'architecture
réclame : une garantie, pas une discipline.

``blake2b``, et jamais ``hash()`` : la fonction de hachage native de Python est
randomisée par ``PYTHONHASHSEED``, donc son résultat change d'un processus à l'autre.
Elle nommerait une collection différente à chaque lancement.
"""

from __future__ import annotations

import json
import math
from hashlib import blake2b
from typing import Any

from pydantic import BaseModel

from .workflow import WorkflowConfig

__all__ = ["canonicalize", "collection_name", "fingerprint"]

# 16 octets → 32 caractères hexadécimaux, la forme d'un run-id MLflow.
_DIGEST_BYTES = 16


def canonicalize(config: WorkflowConfig) -> str:
    """Rend la forme canonique d'une config : une chaîne, une seule, pour toujours.

    Deux configs sémantiquement identiques doivent produire la *même chaîne*, quelles
    que soient l'ordre de déclaration des champs ou la façon dont les nombres ont été
    écrits. C'est ici que se joue la stabilité du hash — le hachage lui-même n'est
    qu'une compression de ce qui sort d'ici.

    Trois règles :

    - **clés triées**, récursivement (``sort_keys``) : l'ordre de déclaration des
      champs d'un modèle ne doit jamais changer le hash ;
    - **floats normalisés** (voir ``_normalize``) : ``0.5``, ``-0.0`` et ``5e-1`` ne
      doivent pas produire trois chaînes ;
    - **séparateurs sans espace et ASCII** : la sérialisation ne doit dépendre ni du
      formatage ni de l'encodage de la plateforme.
    """
    payload = _normalize(config.model_dump(mode="python"))
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(config: WorkflowConfig) -> str:
    """L'empreinte d'une config : 32 caractères hexadécimaux, stables à jamais.

    Ne prend **que** la config de workflow. Lui passer une URI est une erreur de type,
    pas une erreur de jugement.
    """
    canonical = canonicalize(config)
    return blake2b(canonical.encode("utf-8"), digest_size=_DIGEST_BYTES).hexdigest()


def collection_name(config: WorkflowConfig) -> str:
    """Le nom de la collection Qdrant — l'empreinte, et rien d'autre (§6).

    Aucun préfixe lisible : un segment « parlant » redeviendrait le nom fragile que le
    hash remplace. Deux configs ⇒ deux collections qui coexistent, chacune droppable
    indépendamment — c'est la condition de l'A/B.
    """
    return fingerprint(config)


def _normalize(value: Any) -> Any:
    """Ramène une valeur à une forme comparable, en profondeur.

    Le cas qui compte est celui des **floats**. Ils n'apparaissent pas dans la config
    d'aujourd'hui (tailles et dimensions sont des entiers), mais le premier seuil
    flottant qu'on ajoutera passerait par ici sans qu'on y pense — et un ``-0.0``
    hashé différemment de ``0.0`` produirait deux collections pour une seule config,
    sans rien lever.

    ``NaN`` et les infinis sont **refusés** plutôt que sérialisés : ``NaN != NaN``, une
    config qui en contient n'est égale à aucune autre, pas même à elle-même. Un hash
    ne peut rien affirmer d'une telle valeur — mieux vaut le dire que le taire.
    """
    if isinstance(value, BaseModel):
        return _normalize(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, bool):
        # Avant `int` : en Python, `bool` EST un `int`.
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            msg = f"Valeur non hashable dans la config de workflow : {value!r}"
            raise ValueError(msg)
        # `+ 0.0` écrase le zéro négatif ; `repr` d'un float Python fait l'aller-retour
        # sans perte, donc deux floats égaux donnent la même chaîne.
        return repr(value + 0.0)
    return value
