"""``sources/generic`` — **un** parser, **un** chunker, pour six sources.

La thèse de §3 : « un parser par source » est l'inverse du but. On factorise la
mécanique ; les spécificités d'une source sont une **table déclarative** (``RoleTable``),
pas une classe.

De ``sources/legi/`` il ne reste qu'une table et un connecteur. La jurisprudence
n'écrira pas une ligne de parser — elle écrira trois tables.
"""

from .chunking import StructuralChunker
from .normalize import normalize_text
from .parser import GenericParser
from .relations import GenericRelationExtractor
from .role_table import RoleTable
from .roles import Role
from .xml_tree import locate_id, read_root, to_tree

__all__ = [
    "GenericParser",
    "GenericRelationExtractor",
    "Role",
    "RoleTable",
    "StructuralChunker",
    "locate_id",
    "normalize_text",
    "read_root",
    "to_tree",
]
