"""Exceptions du domaine."""

from collections.abc import Mapping

from .models.collision import Collision
from .services.exclusion_reasons import REASON_COLLISION, REASON_FACET_ROOT_DUPLICATED

__all__ = [
    "CollisionError",
    "EmbeddingModelMismatchError",
    "FacetRootCollisionError",
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
    """Le document est lisible, mais il ne satisfait pas une règle métier.

    ``reason`` est l'une des raisons de ``exclusion_reasons`` : obligatoire, pour qu'aucun
    rejet ne finisse dans un fourre-tout.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class CollisionError(ValidationError):
    """Une clé renommée, non déclarée ``list``, a reçu plusieurs valeurs distinctes : la
    table ne dit pas laquelle garder, le document est refusé (ADR-025).

    Elle porte toutes les collisions du document, pour le bilan.
    """

    def __init__(self, message: str, collisions: tuple[Collision, ...]) -> None:
        super().__init__(REASON_COLLISION, message)
        self.collisions = collisions


class FacetRootCollisionError(ValidationError):
    """Plusieurs fichiers d'une clé ont la même racine : sans ordre entre eux, le
    document est refusé (ADR-025).

    ``roots`` : chaque racine en double -> ses fichiers, pour le détail des collisions.
    """

    def __init__(self, message: str, roots: Mapping[str, tuple[str, ...]]) -> None:
        super().__init__(REASON_FACET_ROOT_DUPLICATED, message)
        self.roots = dict(roots)


# Sœur de ValidationError, jamais parente ni fille : parse_documents les distingue par
# un `except ValidationError` placé avant `except ParseError`.
class ParseError(RagCoreError):
    """Le document n'a pas pu être lu (XML malformé, structure inattendue)."""


class TransitNotDrainedError(RagCoreError):
    """``transit_relations`` n'est pas vide en fin de phase 2 : une relation n'a été ni
    écrite, ni mise en attente, ni réduite. Un bug, pas un état dégradé (ADR-034 §6)."""
