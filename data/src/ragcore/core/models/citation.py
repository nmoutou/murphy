"""La citation NON IDENTIFIÉE — une cible décrite en français, jamais un nœud.

**Ce que la mesure a établi.** Un ``<LIEN>`` dont l'``@id`` est vide n'est pas une
scorie : c'est une désignation en toutes lettres, et elle porte du sens. Mesuré sur le
corpus réel (18 juil. 2026) :

- **LEGI** — 89 ``<LIEN>`` sur 16 227 ont l'``@id`` vide ; **89/89 portent du texte**
  (« code de l'environnement », « code des pensions civiles et militaires de retraite »),
  et tous ont un ``typelien`` (40 CITATION, 13 SPEC_APPLI, 12 TXT_SOURCE, 12
  CODIFICATION, 9 CONCORDANCE, 2 TXT_ASSOCIE, 1 CREATION) et un ``sens``.
- **Jurisprudence** — 68 ``<LIEN>`` (tous CASS), **68/68** avec l'``@id`` vide, du texte,
  ``typelien=CITATION`` et ``sens=source``.

Le code affirmait l'inverse côté LEGI (« un libellé d'affichage, une scorie ») et les
JETAIT en silence. C'était faux : les deux sources décrivent leurs cibles **de la même
façon**, avec les deux mêmes attributs porteurs. La règle ne dépend donc pas de la
source — elle dépend de l'identification, et d'elle seule :

    ``@id`` renseigné  → une RELATION (une arête vers un nœud)
    ``@id`` vide       → une CITATION (un champ sur le document)

**Pourquoi un champ et non un nœud ``:Unknown``.** Le placeholder faisait porter au
graphe une entité qui n'en est pas une : « Articles 1103 et 1229 du code civil » est une
*phrase*, pas un document, et aucun run futur ne la fera exister. Un nœud par
formulation, jamais résolu, qui grossit à chaque corpus. La citation est une propriété
de celui qui l'énonce : elle vit sur lui.

**Pourquoi on ne découpe pas la phrase.** Une balise CASS énumère souvent plusieurs
articles d'un coup (« Articles 706-95-16, 706-95-17 et 706-96 du code de procédure
pénale. »). Les séparer demanderait de savoir ce qu'est un code, un article, une
énumération — de la sémantique juridique, précisément ce que ``core/links`` a été
construit pour ne pas contenir. Le texte brut est conservé tel quel ; le découpage
appartient à la passe de résolution.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["Citation"]


class Citation(BaseModel):
    """Une cible DÉCRITE : ce que le document désigne sans pouvoir l'identifier."""

    model_config = ConfigDict(frozen=True)

    text: str
    """La désignation, **brute et intégrale**, telle que la source l'a écrite.

    C'est la seule donnée qui ne peut pas être reconstruite : les attributs sont vides,
    le texte est tout ce qui reste. Ne jamais le normaliser ici.
    """

    verb: str
    """Le verbe de la citation, traduit quand la table le sait, brut sinon.

    Même doctrine que ``Relation.relation_type`` : un mot non traduit entre sous son nom
    plutôt que de disparaître. Il n'est pas un ``ValidatedVerb`` — il ne devient pas un
    type d'arête Neo4j, la contrainte n'a donc pas lieu d'être.
    """

    sens: str = ""
    """Le rôle que le document courant joue dans la citation (``source`` / ``cible``).

    Conservé bien qu'inutilisé aujourd'hui : c'est lui qui permettra d'orienter l'arête
    le jour où la résolution transformera cette citation en relation. Le remesurer
    exigerait de re-parser le XML ; le garder ne coûte rien.
    """
