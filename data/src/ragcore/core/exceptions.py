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

    TEI ne sert qu'UN modèle — celui de son ``--model-id`` — et **ignore** le champ
    ``model`` de la requête. Réclamer `all-mpnet-base-v2` à un service lancé sur
    `gte-base` ne lève rien : on reçoit les vecteurs de `gte-base`, et on les écrit dans
    la collection que le backend interroge avec `all-mpnet-base-v2`. Deux jeux de
    vecteurs incomparables dans un même index, et pas une ligne de log — ça ne se voit
    qu'à la recherche, longtemps après.

    ⚠️ **Cette erreur se lève AVANT le pool, jamais depuis un worker.** ``SagaExecutor``
    attrape ``Exception`` pour compenser : levée dans une step, elle deviendrait un échec
    *par document* — compensé N fois, et le run conclurait « ok » avec N échecs, puisqu'un
    échec partiel ne fait pas échouer le run. Un garde-fou qui dégrade en skip-par-document
    n'est pas un garde-fou. C'est une **précondition du run**, et elle vit dans le hook.
    """


class ValidationError(RagCoreError):
    """Le document est lisible, mais il ne satisfait pas une règle métier
    (identifiant absent, identifiant mal formé, contenu manquant)."""


class CollisionError(ValidationError):
    """Une clé renommée, non déclarée ``list``, a reçu plusieurs valeurs distinctes : la
    table ne dit pas laquelle garder, le document est refusé (ADR-049).

    Elle PORTE toutes les collisions du document : refusé ou non, il les montre au
    bilan.
    """

    def __init__(self, message: str, collisions: tuple[Collision, ...]) -> None:
        super().__init__(message)
        self.collisions = collisions


class ParseError(RagCoreError):
    """Le document n'a pas pu être lu (XML malformé, structure inattendue)."""


# ParseError et ValidationError sont sœurs, jamais l'une sous l'autre :
# parse_documents discrimine `reason="validation_error"` de `reason="parse_error"`
# par un `except ValidationError` placé avant le `except ParseError`. Une relation
# d'héritage entre elles rendrait l'une des deux branches inatteignable.
