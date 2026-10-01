"""La découpe et le modèle d'embedding du run.

``ChunkingConfig`` vient de l'environnement, sans défaut dans le code. Le modèle reste
strict : la conversion des chaînes est faite par ``ChunkingSettings``.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ChunkingConfig", "EmbeddingModel"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ChunkingConfig(_Frozen):
    """En caractères."""

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
    """Le modèle que sert TEI : le nom vient de ``EMBEDDING_MODEL``, la dimension est
    mesurée auprès du service au démarrage.
    """

    model_name: str = Field(min_length=1)
    dimension: int = Field(gt=0)
