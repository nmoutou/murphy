"""Les raisons de collision (``reason`` d'un ``CollisionRecord``) : une raison qui n'est
pas ici n'existe pas.
"""

from .exclusion_reasons import REASON_FACET_ROOT_DUPLICATED

# Une clé de métadonnée a reçu plusieurs valeurs distinctes (ADR-025)
COLLISION_METADATA = "metadata"
# Des copies d'une même racine que le connecteur n'a pas su départager (même date) :
# le document est aussi rejeté, sous la même chaîne
COLLISION_FACET_ROOT_DUPLICATED = REASON_FACET_ROOT_DUPLICATED
# Copies identiques d'une même racine sous une clé : une seule est gardée
COLLISION_DUPLICATE_COPY = "duplicate_copy"
