"""Les raisons de collision (``reason`` d'un ``CollisionRecord``) : une raison qui n'est
pas ici n'existe pas.
"""

from .exclusion_reasons import REASON_FACET_ROOT_DUPLICATED

# Une clé de métadonnée a reçu plusieurs valeurs distinctes (ADR-025)
COLLISION_METADATA = "metadata"
# Plusieurs fichiers d'une clé ont la même racine : le document est aussi rejeté, sous
# la même chaîne
COLLISION_FACET_ROOT_DUPLICATED = REASON_FACET_ROOT_DUPLICATED
