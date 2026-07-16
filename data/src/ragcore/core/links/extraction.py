"""La face EXTRACTION de ``core/links`` : une balise brute devient une arête.

**Le module hégémonique, et ce que ça veut dire.** Un seul module au cœur définit tout
ce qui touche aux liens. Il a deux faces : *extraction* (ici — appelée par le parser) et
*résolution* (la passe de phase 2). Elles partagent le vocabulaire de ``vocabulary.py``.
**Personne d'autre ne fabrique de lien.** ``sources/legi/relations.py`` en fabriquait un,
avec sa propre notion d'orientation et sa propre table : c'est exactement ce qui a permis
au bug des 16 227 liens perdus d'exister sans que le domaine s'en aperçoive.

**Ce que la source apporte, et ce que le domaine garde.** La source apporte une
``LinkTable`` : *quelles balises portent des liens*, *lesquelles sont structurelles*,
*comment son vocabulaire se traduit*, *comment ses identifiants se typent*. Le domaine
garde la mécanique : lire les attributs, orienter, fabriquer la ``Relation``, et déclarer
ce qu'il n'a pas su nommer. Une source nouvelle écrit une table — pas un extracteur.

**Ce qu'il ne fait plus, et pourquoi c'est le cœur du lot.** L'ancien extracteur rendait
``None`` sur un ``typelien`` inconnu : l'arête était *déclarée perdue* au lieu d'être
*écrite*. Ici, ``translate`` fait entrer le mot brut, et la relation existe. Le seul cas
où aucune arête n'est produite est celui où il n'y a **rien à écrire** : pas
d'identifiant cible, ou un mot qui ne peut pas être un verbe. Une absence de donnée n'est
pas un renoncement.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..models.enums import SourceName
from ..models.identifiers import OwnerId, SourceIdentifier, UnknownRef
from ..models.relation import Relation
from ..services.unknown_categories import (
    CATEGORY_IDENTIFIER,
    CATEGORY_SENS,
    CATEGORY_TYPELIEN,
    declare_unknown,
)
from .vocabulary import CONTAINS, RelationVerb, TranslationTable, translate

__all__ = ["ExtractedLinks", "LinkTable", "extract_links"]


SENS_SOURCE = "source"
SENS_CIBLE = "cible"
"""Les deux rôles qu'un document peut jouer dans une arête qu'il déclare.

``sens="source"`` → *moi → lié*. ``sens="cible"`` → *lié → moi*.

Preuve empirique de cette lecture : l'article ``LEGIARTI000031367659`` (2015) porte des
liens ``sens="cible" typelien="CITATION"`` vers un arrêté de **2024**. Un article de 2015
ne cite pas le futur — c'est donc l'arrêté qui le cite.
"""


@dataclass(frozen=True)
class LinkTable:
    """Ce qu'une SOURCE déclare de ses liens. Une donnée, jamais du code.

    C'est le pendant, pour les arêtes, de la table de rôles pour les balises : la
    saturation d'un corpus la remplit, et un cliquet la fige. Une source nouvelle =
    une table.
    """

    translation: TranslationTable
    """Le vocabulaire de la source vers celui du domaine (``"CITATION" -> cites``).

    Exhaustive AUJOURD'HUI, jamais demain — et c'est prévu : ce qu'elle ne contient pas
    entre sous son nom brut et remonte dans ``unknowns``. Le corpus enseigne son
    vocabulaire ; la table apprend.
    """

    structural_kinds: frozenset[str] = frozenset()
    """Les balises de lien dont l'orientation est connue PAR CONSTRUCTION.

    Une section contient ses articles ; un texte contient ses sections. Ce sens-là ne
    peut pas s'inverser, et ces balises ne portent donc ni ``typelien`` ni ``sens``.
    Elles produisent toutes un ``CONTAINS`` — du document courant VERS le lié.
    """

    ancestor_kinds: frozenset[str] = frozenset()
    """Les balises qui déclarent un ANCÊTRE du document (le ``<CONTEXTE>`` de LEGI).

    L'arête va de l'ancêtre VERS le document courant : orientation fixe, jamais ambiguë.
    C'est la fermeture transitive de la contenance — d'où la réduction, en phase 2.
    """

    identifier_for: Callable[[str], SourceIdentifier] | None = None
    """Comment la source type ses identifiants bruts.

    **Ce n'est pas une élégance, c'est un garde-fou.** Le motif de l'ELI ne regarde pas
    le préfixe : ``ELI(raw="JORFTEXT…")`` est accepté sans broncher, et les 568 arêtes du
    corpus qui pointent vers JORF seraient sérialisées ``eli:JORFTEXT…`` — elles ne
    matcheraient jamais un nœud. Une corruption qui ne lève rien.
    """

    describes_targets: bool = False
    """La source **décrit-elle** ses cibles au lieu de les identifier ?

    ``False`` (LEGI) : les cibles sont des identifiants. Un ``@id`` vide est une **scorie**
    — 89 cas sur 16 227 liens — et le libellé du lien n'est qu'un texte d'affichage
    (« Décret n°2008-171 du 22 février 2008 (Ab) »). En faire une cible peuplerait le
    graphe de nœuds fantômes.

    ``True`` (jurisprudence) : les cibles sont des **phrases**, et il n'y a rien d'autre.
    Mesuré : les 68 ``<LIEN>`` du corpus juri ont **tous** leurs attributs vides et
    portent « Articles 1103 et 1229 du code civil ». Sans ce drapeau, leur graphe est vide.

    **Un drapeau, et non une déduction du genre « si l'id est vide, prends le libellé ».**
    La règle implicite serait fausse pour LEGI : elle transformerait ses 89 scories en
    nœuds. C'est à la source de dire comment elle désigne ses cibles — c'est un fait sur
    elle, pas une heuristique sur les données.
    """


@dataclass(frozen=True)
class ExtractedLinks:
    """Ce que l'extraction a produit — et ce qu'elle n'a pas su nommer.

    L'inconnu n'est pas une erreur : c'est une DONNÉE. Il voyage donc dans la donnée,
    exactement comme une arête différée voyage dans ``RelationWriteResult.pending``.
    L'appelant, qui tient une ``WorkerTelemetry``, le déclarera.
    """

    relations: list[Relation] = field(default_factory=list)
    unknowns: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class _Subject:
    """Le document dont on extrait les liens — les trois faits qui ne varient jamais.

    ``current``, ``owner_id`` et ``source`` voyagent ensemble d'un bout à l'autre de
    l'extraction : ils ne décrivent pas trois paramètres, ils décrivent *un* document.
    Les nommer évite de les repasser trois par trois, et rend visible qu'une arête est
    toujours construite **relativement à quelqu'un** — ce que le ``owner_id`` dans la clé
    des pendantes (§13) dit déjà par ailleurs.
    """

    current: SourceIdentifier
    owner_id: OwnerId
    source: SourceName


def extract_links(  # noqa: PLR0913 — six faits distincts, tous nommés : les grouper cacherait ce qu'on assemble
    *,
    references: Sequence[Mapping[str, Any]],
    ancestors: Sequence[Mapping[str, Any]],
    table: LinkTable,
    current: SourceIdentifier,
    owner_id: OwnerId,
    source: SourceName,
) -> ExtractedLinks:
    """Traduit les liens relevés par le parser en arêtes du domaine.

    Le parser a déjà fait son travail : il a relevé les ``<LIEN>`` **bruts** (avec le
    vocabulaire de la source : ``typelien``, ``sens``, ``id``) et les ancêtres. Il ne les
    a pas typés — le faire aurait mis la table de traduction dans deux modules à la fois.

    Ici, le domaine traduit. Ce qu'il ne sait pas traduire, il l'INGÈRE SOUS SON NOM BRUT
    et le déclare. Il ne le jette pas.
    """
    subject = _Subject(current=current, owner_id=owner_id, source=source)
    relations: list[Relation] = []
    unknowns: dict[str, list[str]] = {}

    for reference in references:
        relation = _from_reference(reference, table, subject, unknowns)
        if relation is not None:
            relations.append(relation)

    for ancestor in ancestors:
        relation = _from_ancestor(ancestor, table, subject, unknowns)
        if relation is not None:
            relations.append(relation)

    return ExtractedLinks(relations=relations, unknowns=unknowns)


def _from_reference(
    reference: Mapping[str, Any],
    table: LinkTable,
    subject: _Subject,
    unknowns: dict[str, list[str]],
) -> Relation | None:
    linked = _target(reference, table, unknowns)
    if linked is None:
        # Ni identifiant, ni libellé : il n'y a **rien** — pas même une description. Ce
        # n'est pas un renoncement, c'est l'absence de donnée. La déclarer en `unknowns`
        # polluerait le bilan avec un mot qui n'existe pas.
        return None

    kind = reference.get("kind", "")

    if kind in table.structural_kinds:
        # Orientation par construction : le document courant CONTIENT le lié.
        return _relation(subject.current, linked, CONTAINS, subject, {"kind": kind})

    raw_typelien = reference.get("typelien", "")
    relation_verb, known = translate(table.translation, raw_typelien)

    if relation_verb is None:
        # Le mot ne peut pas ÊTRE un verbe (vide, caractères interdits) : il n'y a rien
        # à écrire dans le graphe. Ce n'est pas un renoncement — c'est l'absence de mot.
        declare_unknown(unknowns, CATEGORY_TYPELIEN, raw_typelien or "<vide>")
        return None

    if not known:
        # Le verbe entre dans le graphe SOUS SON NOM BRUT, et le fait est déclaré.
        # L'arête existe : c'est là toute la différence avec la version qu'on remplace.
        declare_unknown(unknowns, CATEGORY_TYPELIEN, raw_typelien)

    raw_sens = reference.get("sens", "")
    oriented = _orient(subject.current, linked, raw_sens)
    if oriented is None:
        # Une arête qu'on ne sait pas orienter, on ne l'écrit pas au hasard : un graphe
        # faux ne se distingue pas d'un graphe vrai. On dit qu'on n'a pas su.
        declare_unknown(unknowns, CATEGORY_SENS, raw_sens or "<vide>")
        return None

    edge_source, edge_target = oriented
    return _relation(
        edge_source,
        edge_target,
        relation_verb,
        subject,
        # Le vocabulaire d'origine SURVIT — même quand il a été traduit. `references`
        # recouvre neuf `typelien` distincts : sans cette trace, « CODIFICATION » et
        # « CONCORDANCE » deviendraient indiscernables une fois en base.
        {"typelien": raw_typelien, "sens": raw_sens},
    )


def _from_ancestor(
    ancestor: Mapping[str, Any],
    table: LinkTable,
    subject: _Subject,
    unknowns: dict[str, list[str]],
) -> Relation | None:
    """L'ancêtre CONTIENT le document courant. Orientation fixe, jamais ambiguë."""
    if ancestor.get("kind") not in table.ancestor_kinds:
        return None

    linked = _identifier(ancestor.get("id", ""), table, unknowns)
    if linked is None:
        return None

    return _relation(
        linked,
        subject.current,
        CONTAINS,
        subject,
        {"kind": ancestor.get("kind", "")},
    )


def _orient(
    current: SourceIdentifier, linked: SourceIdentifier, sens: str
) -> tuple[SourceIdentifier, SourceIdentifier] | None:
    """Oriente l'arête selon le RÔLE que le document courant y joue.

    Rend ``None`` si le ``sens`` est inconnu — l'appelant le déclare. C'est ce qui
    remplace l'ancien ``_invert``, lequel ajoutait l'arête inverse **en plus** de
    l'originale : il DOUBLAIT chaque relation et rendait le graphe symétrique. Ici, un
    lien donne exactement une arête, orientée à la construction et jamais retournée.
    """
    if sens == SENS_SOURCE:
        return current, linked
    if sens == SENS_CIBLE:
        return linked, current
    return None


def _target(
    reference: Mapping[str, Any],
    table: LinkTable,
    unknowns: dict[str, list[str]],
) -> SourceIdentifier | None:
    """La cible d'un lien : **identifiée** si on peut, **décrite** sinon.

    Deux façons de désigner une cible, et il faut les deux — c'est une mesure, pas une
    précaution :

    1. **Par identifiant** (``@id``, ``@cidtexte``…). LEGI fait ça : ``LEGIARTI000006419264``.
    2. **Par description**, quand aucun identifiant n'est donné. La jurisprudence fait ça,
       et **exclusivement** : les 68 ``<LIEN>`` du corpus juri ont tous leurs attributs
       vides et portent du texte — « Articles 1103 et 1229 du code civil ». La cour décrit
       l'article en français ; elle ne le référence pas.

    Ne gérer que le premier cas — ce que faisait ce module — rendait le graphe de
    jurisprudence **vide, en silence**. La citation existe pourtant : elle est écrite noir
    sur blanc dans l'arrêt.

    La cible décrite devient un ``UnknownRef`` : un nœud qui porte la phrase, et vers
    lequel l'arête pointe. *« Ce qui n'est pas encore résolu n'est pas un état spécial —
    c'est un node unknown qui attend sa passe de résolution. »* On ne parse pas la phrase
    ici : ``core/links`` ne sait pas ce qu'est un code juridique, et le lui apprendre
    remettrait de la sémantique là où on vient de l'en sortir.
    """
    identified = _identifier(reference.get("id", ""), table, unknowns)
    if identified is not None:
        return identified

    if not table.describes_targets:
        # La source est censée identifier ses cibles. Un `id` vide y est une scorie (89
        # cas sur 16 227 chez LEGI), pas une description — en faire un `UnknownRef`
        # peuplerait le graphe de nœuds fantômes portant des libellés d'affichage.
        return None

    label = str(reference.get("label", "")).strip()
    if not label:
        return None
    return UnknownRef(raw=label)


def _identifier(
    raw_id: str, table: LinkTable, unknowns: dict[str, list[str]]
) -> SourceIdentifier | None:
    if not raw_id or table.identifier_for is None:
        # `@id` vide ou source qui n'identifie pas : une ABSENCE, pas un inconnu.
        return None
    try:
        return table.identifier_for(raw_id)
    except Exception:
        # `@id` présent mais illisible : la source a écrit une référence qu'on ne sait
        # pas transformer. La taire ferait disparaître l'arête en silence ; on la
        # DÉCLARE, pour que le bilan la porte et que la table apprenne.
        declare_unknown(unknowns, CATEGORY_IDENTIFIER, raw_id)
        return None


def _relation(
    edge_source: SourceIdentifier,
    edge_target: SourceIdentifier,
    relation_verb: RelationVerb,
    subject: _Subject,
    metadata: Mapping[str, Any],
) -> Relation:
    return Relation(
        source_identifier=edge_source,
        target_identifier=edge_target,
        relation_type=relation_verb,
        owner_id=subject.owner_id,
        source=subject.source,
        metadata={key: value for key, value in metadata.items() if value},
    )
