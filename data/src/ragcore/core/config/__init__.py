"""La config qui change le RÉSULTAT — et rien d'autre.

Ce package ne contient que ce dont une modification **invalide les vecteurs déjà
produits**. L'infrastructure (URIs, secrets, chemins, nombre de workers) vit dans
``adapters/config/`` et n'entre jamais ici.

La frontière n'est pas du rangement : c'est ce qui rend l'A/B possible (§6). Voir
``fingerprint.py``.
"""

from .fingerprint import canonicalize, collection_name, fingerprint
from .workflow import (
    ChunkingConfig,
    EmbeddingConfig,
    NormalizationConfig,
    WorkflowConfig,
)

__all__ = [
    "ChunkingConfig",
    "EmbeddingConfig",
    "NormalizationConfig",
    "WorkflowConfig",
    "canonicalize",
    "collection_name",
    "fingerprint",
]
