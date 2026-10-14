"""Le format XML de la jurisprudence : CAPP, CASS, INCA, JADE et CONSTIT.

Trois tables, aucune mécanique : connecteur, parser et chunker viennent de
``sources/generic``, les liens de ``core/links``.
"""

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
]
