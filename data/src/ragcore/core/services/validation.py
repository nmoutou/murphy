"""Règles de validation de format, réutilisables hors du modèle."""

import re

from ..models.identifiers import ELI_PATTERN

__all__ = ["validate_eli_format"]


def validate_eli_format(value: str) -> bool:
    """Vrai si ``value`` est un ELI bien formé (8 majuscules + 12 chiffres)."""
    return bool(re.match(ELI_PATTERN, value))
