"""Ce que le run traite : la découpe, et le modèle d'embedding.

``ChunkingConfig`` est lu de l'environnement (``ChunkingSettings`` :
``CHUNKING_MAX_CHARS``, ``CHUNKING_OVERLAP_CHARS``) en tête de run. Une variable absente
ou invalide arrête le run : aucun défaut dans le code. Le modèle reste strict : la
conversion des chaînes de l'environnement est faite par ``ChunkingSettings``, pas ici.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ChunkingConfig", "EmbeddingModel"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ChunkingConfig(_Frozen):
    """La découpe : taille maximale d'un chunk et recouvrement, en caractères."""

    max_chars: int = Field(gt=0)
    overlap_chars: int = Field(ge=0)

    @model_validator(mode="after")
    def _overlap_inferieur_a_la_taille(self) -> Self:
        """Sinon le curseur de la fenêtre glissante n'avance pas : boucle infinie."""
        if self.overlap_chars >= self.max_chars:
            raise ValueError(
                f"overlap_chars ({self.overlap_chars}) doit être strictement inférieur "
                f"à max_chars ({self.max_chars})"
            )
        return self


class EmbeddingModel(_Frozen):
    """Le modèle que sert TEI, et la dimension de ses vecteurs.

    Ce n'est pas un réglage : le nom vient de ``EMBEDDING_MODEL``, la dimension est
    mesurée auprès du service au démarrage. La collection Qdrant est créée à cette
    dimension, et le backend interroge le même modèle.
    """

    model_name: str = Field(min_length=1)
    dimension: int = Field(gt=0)
