"""La relation non formatée — une cible décrite en toutes lettres, jamais un nœud
(ADR-045).

LEGI et la jurisprudence décrivent leurs cibles de la même façon : un ``<LIEN>`` à
``@id`` vide porte une désignation (« code de l'environnement »). La règle ne dépend que
de l'identification :

    ``@id`` renseigné  → une ``Relation`` (une arête vers un nœud)
    ``@id`` vide       → une ``UnformattedRelation`` (une ligne d'``unformatted_relations``)

La phrase n'est pas découpée (« Articles 706-95-16, 706-95-17 et 706-96 du code de
procédure pénale ») : ce serait de la sémantique juridique, que ``core/links`` ne
contient pas. Le découpage appartient à la passe de résolution.
"""

from pydantic import BaseModel, ConfigDict

from .enums import SourceName
from .identifiers import Identifier

__all__ = ["UnformattedRelation"]


class UnformattedRelation(BaseModel):
    """Ce que le document désigne sans l'identifier."""

    model_config = ConfigDict(frozen=True)

    source_identifier: Identifier
    """Le document qui énonce la relation."""

    target_text: str
    """Brute et intégrale, telle que la source l'a écrite : c'est tout ce qui reste de la
    cible. Ne jamais la normaliser ici."""

    relation_type: str
    """Traduit quand la table le sait, brut sinon. Pas un ``ValidatedVerb`` : il ne
    devient pas un type d'arête Neo4j."""

    sens: str = ""
    """Le rôle du document courant dans la relation (``source`` / ``cible``).

    Inutilisé, mais il orientera l'arête quand la résolution en fera une ; le retrouver
    exigerait de re-parser le XML.
    """

    source: SourceName
