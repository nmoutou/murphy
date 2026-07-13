"""Le vocabulaire de la jurisprudence — et **la découverte qui a changé le lot**.

**Les liens de la jurisprudence n'ont pas de cible.** Mesuré sur les 352 fichiers du
corpus : les 68 ``<LIEN>`` ont **tous leurs attributs vides** — ni ``id``, ni ``cidtexte``,
ni ``nortexte``, ni ``numtexte``. Ce qu'ils portent, c'est du **texte** :

    « Articles 1103 et 1229 du code civil. »
    « Article L. 225-149-3, dans sa rédaction alors applicable ; article L. 225-147… »
    « Sur le numéro 2 : Article 1920 du code général des impôts, dans sa version issue
      de la loi n° 2021-1900 du 30 décembre 2021 »

Ce ne sont pas des identifiants mal remplis. C'est une **citation en langue naturelle** :
la cour *décrit* l'article qu'elle vise, en français, comme le ferait un juriste. Elle ne
le référence pas.

**Conséquence, et c'est ce qui a failli passer en silence.** ``core/links`` traitait un
lien sans identifiant comme une *donnée absente* — ce qui est vrai pour LEGI (89 attributs
vides sur 16 227, des scories) et radicalement faux ici, où c'est **le cas normal, à
100 %**. Sans ``describes_targets=True``, le graphe de jurisprudence aurait été **vide**,
et rien ne l'aurait signalé : les 68 citations se seraient évaporées exactement comme les
16 227 liens de LEGI en leur temps.

**Ce que la table livre aujourd'hui, et ce qu'elle ne livre pas.** La citation devient une
arête vers un nœud ``:Unknown`` qui porte la phrase. Le graphe existe, la citation est
visible, elle est interrogeable. Ce qui manque est son *identité* : « Articles 1103 du
code civil » n'est pas encore relié à ``LEGIARTI…``.

Cette résolution est un lot à part, et il faut être clair sur sa difficulté : elle demande
un **extracteur de références juridiques** (une phrase → plusieurs références structurées,
avec versions et renumérotations) *en plus* du registre d'alias (§1). Les libellés
mesurés contiennent jusqu'à cinq cibles, des états temporels (« dans sa rédaction issue
de… »), des renumérotations (« devenu L. 821-31 »), des cibles hors-LEGI (conventions
collectives) et des troncatures de la source (« Sur le numéro 1 : té du 10 janvier 1989 »).

**La bonne nouvelle : ce lot-là ne demandera aucune ré-ingestion.** La phrase est déjà dans
le graphe. Résoudre, ce sera fusionner le nœud ``:Unknown`` vers le vrai article — pas
relire 352 fichiers.
"""

from ragcore.core.links import CITES, LinkTable, RelationVerb
from ragcore.core.models.identifiers import DecisionId, SourceIdentifier

__all__ = ["JURI_LINK_TABLE", "TYPELIEN_TO_VERB", "identifier_for"]


TYPELIEN_TO_VERB: dict[str, RelationVerb] = {
    # Mesuré : **un seul** typelien dans tout le corpus juri (68/68 liens), et un seul
    # `sens` (« source »). La jurisprudence ne modifie ni n'abroge — elle cite. C'est
    # cohérent avec ce qu'elle est : un arrêt applique le droit, il ne le fait pas.
    "CITATION": CITES,
}
"""Le vocabulaire de liens de la jurisprudence, tel que le corpus le déclare.

**Exhaustif aujourd'hui — sur 352 fichiers.** Et le corpus est maigre : 1 fichier CAPP,
1 INCA, 2 CONSTIT. Un export complet en révélera d'autres, et c'est prévu : un ``typelien``
absent de cette table **entre quand même** dans le graphe, sous son nom brut, et remonte
dans le ``RunSummary``. La table apprend ; rien ne se perd entre-temps.
"""


def identifier_for(raw_id: str) -> SourceIdentifier:
    """Type l'identifiant d'une décision — ``DecisionId``, **jamais** ``ELI``.

    **Le piège, et il est réel.** ``JURITEXT000019333891`` satisfait parfaitement le motif
    de l'ELI (``^[A-Z]{8}[0-9]{12}$``) : le motif ne regarde pas le préfixe. Un arrêt aurait
    donc été sérialisé ``eli:JURITEXT…`` sans qu'aucune exception ne soit levée, et le
    graphe aurait porté des « textes de loi » dotés d'une formation de jugement.

    C'est exactement le piège des 568 arêtes JORF, qui a déjà été payé une fois du côté de
    LEGI. On ne le repaie pas.

    **Cette fonction ne sert PAS aux cibles de liens** — la juri n'en identifie aucune (cf.
    ``describes_targets``). Elle ne type que l'identifiant du document lui-même, lu dans
    ``<ID>``.
    """
    return DecisionId(raw=raw_id)


JURI_LINK_TABLE = LinkTable(
    translation=TYPELIEN_TO_VERB,
    # La juri n'a **aucun** lien structurel : un arrêt ne contient pas d'autres arrêts.
    # Là où LEGI déclare un arbre (texte ⊃ section ⊃ article), la jurisprudence est plate.
    structural_kinds=frozenset(),
    ancestor_kinds=frozenset(),
    identifier_for=identifier_for,
    # LA ligne qui fait exister le graphe juri. Sans elle, 68 citations disparaissent.
    describes_targets=True,
)
"""Tout ce que la jurisprudence déclare de ses liens — **et c'est peu**.

Un verbe, un sens, aucune structure, aucune cible identifiée. La richesse est ailleurs :
dans la phrase, que le nœud ``:Unknown`` conserve intacte en attendant sa résolution.
"""
