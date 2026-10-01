"""La relation NON FORMATÉE — une cible décrite en français, jamais un nœud.

**Ce que la mesure a établi.** Un ``<LIEN>`` dont l'``@id`` est vide n'est pas une
scorie : c'est une désignation en toutes lettres, et elle porte du sens. Mesuré sur le
corpus réel (18 juil. 2026) :

- **LEGI** — 89 ``<LIEN>`` sur 16 227 ont l'``@id`` vide ; **89/89 portent du texte**
  (« code de l'environnement », « code des pensions civiles et militaires de retraite »),
  et tous ont un ``typelien`` (40 CITATION, 13 SPEC_APPLI, 12 TXT_SOURCE, 12
  CODIFICATION, 9 CONCORDANCE, 2 TXT_ASSOCIE, 1 CREATION) et un ``sens``.
- **Jurisprudence** — 68 ``<LIEN>`` (tous CASS), **68/68** avec l'``@id`` vide, du texte,
  ``typelien=CITATION`` et ``sens=source``.

Les deux sources décrivent leurs cibles **de la même façon**, avec les deux mêmes
attributs porteurs. La règle ne dépend donc pas de la source — elle dépend de
l'identification, et d'elle seule :

    ``@id`` renseigné  → une ``Relation`` (une arête vers un nœud)
    ``@id`` vide       → une ``UnformattedRelation`` (une ligne d'``unformatted_relations``)

**Pourquoi une collection, et ni un nœud ni un champ du document (ADR-045).** « Articles
1103 et 1229 du code civil » est une *phrase*, pas un document : un nœud ``:Unknown`` par
formulation peuplait le graphe d'entités jamais résolues. Ce n'est pas non plus une
propriété du document qui l'énonce : c'est une relation dont la cible attend d'être
résolue, au même titre qu'une pendante. Elle vit donc à côté d'elles, dans sa propre
collection Mongo, et s'y accumule de run en run.

**Pourquoi on ne découpe pas la phrase.** Une balise CASS énumère souvent plusieurs
articles d'un coup (« Articles 706-95-16, 706-95-17 et 706-96 du code de procédure
pénale. »). Les séparer demanderait de savoir ce qu'est un code, un article, une
énumération — de la sémantique juridique, précisément ce que ``core/links`` a été
construit pour ne pas contenir. Le texte brut est conservé tel quel ; le découpage
appartient à la passe de résolution.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import SourceName
from .identifiers import Identifier

__all__ = ["UnformattedRelation"]


class UnformattedRelation(BaseModel):
    """Une relation à cible DÉCRITE : ce que le document désigne sans l'identifier."""

    model_config = ConfigDict(frozen=True)

    source_identifier: Identifier
    """Le document qui énonce la relation."""

    target_text: str
    """La désignation de la cible, **brute et intégrale**, telle que la source l'a écrite.

    C'est la seule donnée qui ne peut pas être reconstruite : les attributs sont vides,
    le texte est tout ce qui reste. Ne jamais le normaliser ici.
    """

    relation_type: str
    """Le verbe de la relation, traduit quand la table le sait, brut sinon.

    Même doctrine que ``Relation.relation_type`` : un mot non traduit entre sous son nom
    plutôt que de disparaître. Il n'est pas un ``ValidatedVerb`` — il ne devient pas un
    type d'arête Neo4j, la contrainte n'a donc pas lieu d'être.
    """

    sens: str = ""
    """Le rôle que le document courant joue dans la relation (``source`` / ``cible``).

    Conservé bien qu'inutilisé aujourd'hui : c'est lui qui permettra d'orienter l'arête
    le jour où la résolution transformera cette relation en arête. Le remesurer
    exigerait de re-parser le XML ; le garder ne coûte rien.
    """

    source: SourceName
    """La source du document qui a déclaré cette relation."""

    metadata: dict[str, Any] = Field(default_factory=dict)
