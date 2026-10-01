"""Le type et la nature d'un document : deux axes, deux lectures.

Le **type** (``DocumentType``) dit la forme du document — article, section, texte,
décision. Il se déduit du préfixe de l'identifiant, la seule donnée présente et validée
sur tous les documents. La **nature** dit sa qualification juridique (``LOI``,
``ARRET``, ``QPC``…) : la balise ``NATURE`` de la source, facultative.
"""

from ragcore.core.exceptions import ValidationError
from ragcore.core.models.enums import DocumentType
from ragcore.core.models.identifiers import Identifier

from .role_table import RoleTable
from .tree import Node, first

__all__ = ["document_type_of", "nature_of"]


def document_type_of(identifier: Identifier, table: RoleTable) -> DocumentType:
    """Le type que la table déclare pour le préfixe de l'identifiant.

    Lève ``ValidationError`` (un refus métier, compté par le run) si la table ne déclare
    pas ce préfixe : aucun document n'entre sans type.
    """
    document_type = table.document_types.get(identifier.prefix)
    if document_type is None:
        declared = ", ".join(sorted(table.document_types)) or "aucun"
        msg = (
            f"Préfixe d'identifiant sans type de document : {identifier.prefix!r} "
            f"({identifier.raw}). Préfixes déclarés : {declared}."
        )
        raise ValidationError(msg)
    return document_type


def nature_of(facets: list[Node], table: RoleTable) -> str | None:
    """La première nature non vide des facettes, en majuscules.

    ``None`` si aucune facette n'en porte, ou si elle figure parmi les natures qui
    n'apportent rien (``uninformative_natures``).
    """
    for facet in facets:
        node = first(facet, table.nature_tag)
        if node is None or not node["text"].strip():
            continue
        nature = node["text"].strip().upper()
        return None if nature in table.uninformative_natures else nature
    return None
