"""Exceptions du domaine."""

from .models.collision import Collision

__all__ = [
    "CollisionError",
    "EmbeddingModelMismatchError",
    "ParseError",
    "RagCoreError",
    "ValidationError",
]


class RagCoreError(Exception):
    """Racine de toutes les erreurs du domaine."""


class EmbeddingModelMismatchError(RagCoreError):
    """Le service d'embedding ne sert pas ``EMBEDDING_MODEL``, ou ne peut pas le prouver.

    TEI ignore le champ ``model`` de la requête et sert son seul ``--model-id`` : sans ce
    contrôle, deux jeux de vecteurs incomparables finiraient dans la même collection,
    sans une ligne de log.

    À lever avant le pool, jamais depuis un worker : ``SagaExecutor`` la compenserait
    document par document et le run conclurait « ok ».
    """


class ValidationError(RagCoreError):
    """Le document est lisible, mais il ne satisfait pas une règle métier
    (identifiant absent, identifiant mal formé, contenu manquant)."""


class CollisionError(ValidationError):
    """Une clé renommée, non déclarée ``list``, a reçu plusieurs valeurs distinctes : la
    table ne dit pas laquelle garder, le document est refusé (ADR-049).

    Elle porte toutes les collisions du document, pour le bilan.
    """

    def __init__(self, message: str, collisions: tuple[Collision, ...]) -> None:
        super().__init__(message)
        self.collisions = collisions


# Sœur de ValidationError, jamais parente ni fille : parse_documents les distingue par
# un `except ValidationError` placé avant `except ParseError`.
class ParseError(RagCoreError):
    """Le document n'a pas pu être lu (XML malformé, structure inattendue)."""
