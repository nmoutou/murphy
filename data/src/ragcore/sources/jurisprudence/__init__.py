"""``sources/jurisprudence`` — cinq sources, **trois tables, un connecteur, zéro parser**.

CAPP, CASS, INCA, JADE, CONSTIT : cinq bases DILA, un seul format XML. Le code est rangé
par format, les données par base ; ``sources/registry.py`` fait le lien. Ce package ne
contient aucune mécanique : le parser et le
chunker sont ceux de ``sources/generic``, la mécanique des liens est celle de
``core/links``. La juri n'apporte que du vocabulaire.

C'est la vérification de §3 : *« une source nouvelle = une table, pas un second parser »*.
Cinq sources sont arrivées ; aucun parser n'a été écrit.
"""

from .file_connector import JuriFileConnector
from .table import (
    JURI_ADMIN_ROLE_TABLE,
    JURI_CONSTIT_ROLE_TABLE,
    JURI_JUDI_ROLE_TABLE,
    ROLE_TABLE_BY_ROOT,
)
from .vocabulary import JURI_LINK_TABLE

__all__ = [
    "JURI_ADMIN_ROLE_TABLE",
    "JURI_CONSTIT_ROLE_TABLE",
    "JURI_JUDI_ROLE_TABLE",
    "JURI_LINK_TABLE",
    "ROLE_TABLE_BY_ROOT",
    "JuriFileConnector",
]
