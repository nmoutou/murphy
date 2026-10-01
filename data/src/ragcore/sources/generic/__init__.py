"""Un parser, un chunker, pour toutes les sources : les spécificités d'une source sont
une table déclarative (``RoleTable``), pas une classe.
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
