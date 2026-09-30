"""Les réglages du traitement : la découpe, et le modèle d'embedding.

Lus de ``parameters.yml`` (blocs ``chunking`` et ``embedding``) en tête de run. Un champ
absent, mal typé ou inconnu arrête le run : aucun défaut dans le code, et aucune
conversion (``"384"`` n'est pas un entier).
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ChunkingConfig", "EmbeddingConfig"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ChunkingConfig(_Frozen):
    """La découpe : taille maximale d'un chunk et recouvrement, en caractères."""

    size: int = Field(gt=0)
    overlap: int = Field(ge=0)


class EmbeddingConfig(_Frozen):
    """Le modèle d'embedding et la dimension de ses vecteurs.

    La collection Qdrant est créée à cette dimension, et le backend doit interroger le
    même modèle.
    """

    model_name: str = Field(min_length=1)
    dimension: int = Field(gt=0)
