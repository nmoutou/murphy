"""La config qui ne change PAS le résultat — le *où* et le *comment*.

Déménager Mongo, changer un mot de passe, doubler le nombre de workers : les vecteurs
produits sont identiques au bit près. Rien d'ici n'entre dans le hash de collection
(§6) — voir ``ragcore.core.config`` pour l'autre moitié, et pourquoi la frontière est
structurelle.
"""

from .settings import (
    EmbeddingRuntimeSettings,
    InfraSettings,
    get_embedding_runtime_settings,
    get_infra_settings,
)

__all__ = [
    "EmbeddingRuntimeSettings",
    "InfraSettings",
    "get_embedding_runtime_settings",
    "get_infra_settings",
]
