"""Les quatre rôles — ce qu'une balise PEUT être, et rien d'autre.

**La thèse de §3, en un mot.** « Un parser par source » est rejeté : c'est l'inverse du
but. On factorise la mécanique de traitement ; les spécificités d'une source sont une
**table déclarative** — chaque balise porte un rôle — et non des classes séparées.

**Pourquoi quatre, et pas trois ni douze.** Ces quatre rôles sont les quatre *axes de
traitement non-standard* mesurés en croisant les notebooks de jurisprudence et le code
LEGI. Ils ne sont pas une taxonomie inventée : chacun correspond à un traitement qu'on
ne sait pas faire génériquement, et qui doit donc être nommé.

- ``BODY``    — le texte du document. Il part dans Mongo et dans l'embedding.
- ``LINK``    — une arête. Elle part dans ``core/links``, jamais traitée ici.
- ``VERSION`` — l'axe temporel (``date_debut``/``date_fin``/``etat``). **Absent de la
                jurisprudence** : le rôle existe toujours, aucune balise n'y est mappée,
                le handler ne s'active pas. Un rôle optionnel *nommé* vaut mieux qu'un
                axe temporel dissous dans les métadonnées — le jour où le serving veut
                filtrer « en vigueur au 12/07 », il faut que quelque chose porte ce sens.
- ``META``    — le fourre-tout **légitime** : tout champ plat qui n'est ni du corps, ni
                un lien, ni une date de version. C'est le rôle par défaut *déclaré*, pas
                le rôle par défaut *implicite* : une balise doit y être mappée
                explicitement, sinon elle ressort en ``unknowns``. Le rôle ne suffit
                pas à la configurer : sans renommage dans ``meta_renames``, elle reste
                non-configurée (ADR-047).

**Ce que la table N'EST PAS.** Ce n'est pas une validation, et le rôle ne réintroduit pas
de typage métier (§2) : ``doc_type`` ne fait que *choisir la table*. Il n'y a pas de
classe ``Article`` et de classe ``Arrêt`` — il y a des tables, qui sont des données.

**Le cliquet qui la rend vraie.** Une balise sans rôle **ne disparaît pas** : elle
ressort dans ``unknowns["balise"]``, et le golden test la fait échouer. C'est le même
dispositif que le catalogue d'events (§12) : *rien n'entre en silence*. La saturation du
corpus réconcilie la table ; elle ne la contourne pas.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Role"]


class Role(StrEnum):
    """Le rôle d'une balise dans le traitement. Un seul par balise, jamais deux.

    ``StrEnum`` et non ``str`` : contrairement au verbe d'une relation (dont le
    vocabulaire est *ouvert*, parce qu'il vient des sources), les rôles sont une décision
    d'**architecture**. Le domaine les possède entièrement. Un cinquième rôle ne peut pas
    « arriver du corpus » — il faudrait l'écrire, avec son handler. Ici, l'énumération
    fermée dit la vérité.
    """

    BODY = "body"
    LINK = "link"
    VERSION = "version"
    META = "meta"
