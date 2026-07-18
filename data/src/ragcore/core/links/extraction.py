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

from ..models.citation import Citation
from ..models.enums import SourceName
from ..models.identifiers import OwnerId, SourceIdentifier
from ..models.relation import Relation
from ..services.unknown_categories import (
    CATEGORY_IDENTIFIER,
    CATEGORY_SENS,
    CATEGORY_TYPELIEN,
    declare_unknown,
)
from .vocabulary import (
    CONTAINS,
    REFERENCES,
    SUCCEEDED_BY,
    RelationVerb,
    TranslationTable,
    translate,
)

__all__ = [
    "HEURISTIC_KIND",
    "STILLBORN_SUFFIX",
    "VERSION_KIND",
    "Citation",
    "ExtractedLinks",
    "LinkTable",
    "extract_links",
]


VERSION_KIND = "version:lien"
"""Le ``kind`` des liens de VERSION — l'axe temporel d'un document.

Chaque ``<LIEN_ART>`` d'un bloc ``<VERSIONS>`` désigne une version datée du MÊME
article — JAMAIS une contenance (le bloc était exclu de ``link_containers`` à raison :
le traduire ainsi créerait cycles et faux parents). Ces références ne deviennent pas des
arêtes une à une : elles sont traitées **en groupe** par ``_version_chain``, qui trie la
liste par ``debut`` et n'émet que les arêtes de la CHAÎNE touchant le document courant.
L'auto-référence n'est plus jetée : elle est l'**ancre** qui localise le document dans
sa propre liste.
"""

STILLBORN_SUFFIX = "_MORT_NE"
"""Le marqueur DILA d'une version JAMAIS entrée en vigueur (``MODIFIE_MORT_NE``…).

Un texte A modifie un article avec effet différé ; un texte B révoque la disposition
avant l'échéance : la version qu'A aurait produite est *mort-née* — son ``fin`` est
souvent antérieur à son ``debut``. Le suffixe est le critère fiable, PAS les dates :
mesuré sur le corpus, 12 liens mort-nés sur 57 ont des dates d'apparence normale.
Poids juridique nul (personne n'a jamais été régi par elle) : elle est HORS de la
chaîne, accrochée en branche latérale — l'``etat`` voyage sur l'arête pour la filtrer.
"""

HEURISTIC_KIND = "unconfigured:dila_id"
"""Le ``kind`` des références produites par la CASCADE du parser (cadrage B-00-d).

Une balise NON-CONFIGURÉE dont la valeur a la forme d'un identifiant DILA (et n'est pas
le document lui-même) est une donnée qui *pointe* : elle passe la porte « liens », pas
la porte « metadata ». Le parser l'émet sous ce kind — sans ``typelien`` ni ``sens``,
puisque la source n'a rien déclaré — et le domaine la traduit ici en arête
``references``, du document courant VERS la cible. Le verbe générique est assumé : on
sait QUE ça pointe, pas POURQUOI ; le jour où la table apprend la balise, elle prendra
un rôle déclaré et un verbe précis.
"""


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


@dataclass(frozen=True)
class ExtractedLinks:
    """Ce que l'extraction a produit — et ce qu'elle n'a pas su nommer.

    L'inconnu n'est pas une erreur : c'est une DONNÉE. Il voyage donc dans la donnée,
    exactement comme une arête différée voyage dans ``RelationWriteResult.pending``.
    L'appelant, qui tient une ``WorkerTelemetry``, le déclarera.
    """

    relations: list[Relation] = field(default_factory=list)
    unknowns: dict[str, list[str]] = field(default_factory=dict)

    citations: list[Citation] = field(default_factory=list)
    """Les cibles DÉCRITES — celles dont l'``@id`` était vide.

    Elles ne sont pas des arêtes et n'en produiront aucune : elles remontent vers le
    document, qui les porte en propre. Voir ``core.models.citation``.
    """


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
    citations: list[Citation] = []
    unknowns: dict[str, list[str]] = {}

    # Les liens de VERSION se traitent EN GROUPE : la chaîne est une propriété de la
    # liste (l'ordre), pas de chaque lien pris isolément. Les traduire un à un — c'est
    # ce que faisait `has_version` — produit le produit cartésien : 2 760 arêtes « dans
    # tous les sens » là où ~350 suffisent à porter le même fait.
    versions = [r for r in references if r.get("kind", "") == VERSION_KIND]
    relations.extend(_version_chain(versions, table, subject, unknowns))

    for reference in references:
        if reference.get("kind", "") == VERSION_KIND:
            continue
        extracted = _from_reference(reference, table, subject, unknowns)
        # Deux natures, un seul aiguillage — l'identification de la cible. Le `match`
        # dit lequel des deux plans reçoit la balise : le graphe, ou le document.
        match extracted:
            case Relation():
                relations.append(extracted)
            case Citation():
                citations.append(extracted)
            case None:
                pass

    for ancestor in ancestors:
        relation = _from_ancestor(ancestor, table, subject, unknowns)
        if relation is not None:
            relations.append(relation)

    return ExtractedLinks(relations=relations, unknowns=unknowns, citations=citations)


def _dating(reference: Mapping[str, Any]) -> dict[str, Any]:
    """La datation d'une version, extraite de sa référence — elle finit sur l'arête.

    C'est elle qui rend la ligne de vie lisible dans le graphe (``debut``/``fin``/
    ``etat``/``num``), et c'est l'``etat`` qui permet d'écarter les mort-nées d'une
    requête sans casser la chaîne.
    """
    return {k: v for k, v in reference.items() if k not in ("kind", "id")}


def _is_stillborn(reference: Mapping[str, Any]) -> bool:
    return str(reference.get("etat", "")).endswith(STILLBORN_SUFFIX)


def _version_chain(
    versions: Sequence[Mapping[str, Any]],
    table: LinkTable,
    subject: _Subject,
    unknowns: dict[str, list[str]],
) -> list[Relation]:
    """La CHAÎNE temporelle : chaque version pointe sa suivante, dans le sens du temps.

    Le document courant n'émet que les arêtes **qui le touchent** — sortante ET
    entrante : « ma version précédente → moi » et « moi → ma version suivante ». Chaque
    arête est ainsi émise par ses deux bouts, et le ``MERGE`` dédoublonne : la chaîne
    survit à un maillon absent du corpus sans qu'aucun document n'ait à coordonner quoi
    que ce soit avec un autre.

    L'**auto-référence** — le bloc ``<VERSIONS>`` liste toujours l'article lui-même —
    n'est plus jetée : elle est l'ancre qui localise le document dans sa propre liste
    triée. Sans elle, il n'y a rien à émettre (le document ne sait pas où il est).

    Les **mort-nées** sont hors chaîne : jamais entrées en vigueur, elles n'ont aucune
    date où elles furent le droit applicable — les chaîner affirmerait le contraire.
    Elles s'accrochent en branche latérale à la version en vigueur au moment de
    l'avortement (la dernière vivante avant leur ``debut`` théorique), l'``etat`` sur
    l'arête disant ce qu'elles sont.
    """
    entries = [
        (reference, identified)
        for reference in versions
        if (identified := _identifier(reference.get("id", ""), table, unknowns))
        is not None
    ]
    if not entries:
        return []

    living = sorted(
        (e for e in entries if not _is_stillborn(e[0])),
        key=lambda e: (str(e[0].get("debut", "")), str(e[0].get("fin", ""))),
    )
    me = subject.current.serialize()
    relations: list[Relation] = []

    position = next(
        (i for i, (_, ident) in enumerate(living) if ident.serialize() == me), None
    )
    if position is not None:
        if position > 0:
            prev_ref, prev_id = living[position - 1]
            my_ref, _ = living[position]
            relations.append(
                _relation(
                    prev_id, subject.current, SUCCEEDED_BY, subject, _dating(my_ref)
                )
            )
        if position < len(living) - 1:
            next_ref, next_id = living[position + 1]
            relations.append(
                _relation(
                    subject.current, next_id, SUCCEEDED_BY, subject, _dating(next_ref)
                )
            )
        # Les mort-nées dont JE suis la version en vigueur au moment de l'avortement :
        # ma branche latérale sortante.
        for reference, identified in entries:
            if not _is_stillborn(reference):
                continue
            anchor = _anchor(living, str(reference.get("debut", "")))
            if anchor is not None and anchor[1].serialize() == me:
                relations.append(
                    _relation(
                        subject.current,
                        identified,
                        SUCCEEDED_BY,
                        subject,
                        _dating(reference),
                    )
                )
        return relations

    # JE suis peut-être une mort-née : mon arête entrante vient de la version vivante
    # en vigueur au moment de l'avortement. Pas d'arête sortante — une version jamais
    # née n'a pas de suite.
    mine = next(
        (r for r, ident in entries if ident.serialize() == me and _is_stillborn(r)),
        None,
    )
    if mine is not None:
        anchor = _anchor(living, str(mine.get("debut", "")))
        if anchor is not None:
            relations.append(
                _relation(
                    anchor[1], subject.current, SUCCEEDED_BY, subject, _dating(mine)
                )
            )
    return relations


def _anchor(
    living: Sequence[tuple[Mapping[str, Any], SourceIdentifier]], debut: str
) -> tuple[Mapping[str, Any], SourceIdentifier] | None:
    """La version en vigueur au moment de l'avortement d'une mort-née.

    C'est la dernière vivante dont le ``debut`` est STRICTEMENT antérieur au ``debut``
    théorique de la mort-née — laquelle partage précisément ce ``debut`` avec la version
    réelle qui l'a remplacée (mesuré : les 45 doublons de ``debut`` du corpus sont tous
    ce cas). Un tri qui les confondrait est exactement ce que la branche latérale évite.
    """
    candidates = [e for e in living if str(e[0].get("debut", "")) < debut]
    return candidates[-1] if candidates else None


def _from_reference(  # noqa: PLR0911 — chaque `return` est une ISSUE de la cascade (heuristique, structurel, non-orientable…) ; les fusionner cacherait laquelle a décidé
    reference: Mapping[str, Any],
    table: LinkTable,
    subject: _Subject,
    unknowns: dict[str, list[str]],
) -> Relation | Citation | None:
    """Une balise brute devient une ARÊTE si sa cible est identifiée, une CITATION sinon.

    L'``@id`` est le seul aiguillage. Ce qui est identifié rejoint le graphe ; ce qui est
    seulement décrit rejoint le document. Rien n'est jeté au passage — c'était le défaut
    de la version précédente, qui perdait 89 liens LEGI sans le dire.
    """
    kind = reference.get("kind", "")

    if kind == HEURISTIC_KIND:
        # La cascade du parser a reconnu une valeur au format DILA sur une balise
        # non-configurée. Pas de `typelien`, pas de `sens` : la source n'a rien déclaré.
        # Orientation par construction (le document courant PORTE la référence), verbe
        # générique `references`. La balise d'origine survit en métadonnée d'arête —
        # c'est elle qui dira, plus tard, quoi apprendre à la table.
        linked = _identifier(reference.get("id", ""), table, unknowns)
        if linked is None:
            return None
        return _relation(
            subject.current,
            linked,
            REFERENCES,
            subject,
            {"kind": reference.get("tag", ""), "origin": "heuristic"},
        )

    linked = _identifier(reference.get("id", ""), table, unknowns)
    if linked is None:
        # Pas d'identifiant : la cible est DÉCRITE, ou elle n'est rien. `_citation` rend
        # `None` dans le second cas — ni identifiant, ni texte, il n'y a pas de donnée.
        # La déclarer en `unknowns` polluerait le bilan avec un mot qui n'existe pas.
        return _citation(reference, table)

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


def _citation(
    reference: Mapping[str, Any],
    table: LinkTable,
) -> Citation | None:
    """La cible DÉCRITE : un champ sur le document, **jamais** un nœud du graphe.

    Appelée quand l'``@id`` est vide — et c'est le seul critère. Ni la source, ni un
    drapeau déclaratif : l'identification, ou son absence. Le ``describes_targets`` qui
    régnait ici distinguait « le vide est la norme » (juri) de « le vide est une scorie »
    (LEGI) ; la mesure du corpus a montré que cette seconde moitié était fausse — les 89
    ``<LIEN>`` LEGI à ``@id`` vide portent **tous** un texte de désignation et un
    ``typelien``, exactement comme les 68 de la jurisprudence. Le drapeau ne protégeait
    d'aucun bruit : il jetait 89 citations réelles en silence.

    Rend ``None`` s'il n'y a pas même un texte : une balise sans identifiant ET sans
    désignation ne dit rien du tout. Ce n'est pas un renoncement, c'est une absence.

    Le verbe suit la doctrine de ``Relation.relation_type`` : traduit si la table le
    sait, brut sinon. Un mot non traduit entre sous son nom plutôt que de disparaître.
    """
    text = str(reference.get("label", "")).strip()
    if not text:
        return None

    raw_typelien = str(reference.get("typelien", ""))
    verb, _ = translate(table.translation, raw_typelien)
    return Citation(
        text=text,
        verb=str(verb) if verb is not None else raw_typelien,
        sens=str(reference.get("sens", "")),
    )


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
