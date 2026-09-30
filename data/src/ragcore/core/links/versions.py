"""La CHAÎNE temporelle des versions d'un document — l'axe du temps du graphe.

Les liens de version se traitent EN GROUPE : la chaîne est une propriété de la liste
(l'ordre), pas de chaque lien pris isolément. Les traduire un à un — c'est ce que faisait
`has_version` — produit le produit cartésien : 2 760 arêtes « dans tous les sens » là où
~350 suffisent à porter le même fait.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..models.identifiers import Identifier
from ..models.relation import Relation
from .subject import LinkSubject
from .vocabulary import SUCCEEDED_BY

__all__ = ["STILLBORN_SUFFIX", "VERSION_KIND", "VersionEntry", "version_chain"]


VERSION_KIND = "version:lien"
"""Le ``kind`` des liens de VERSION — l'axe temporel d'un document.

Chaque ``<LIEN_ART>`` d'un bloc ``<VERSIONS>`` désigne une version datée du MÊME
article — JAMAIS une contenance (le bloc était exclu de ``link_containers`` à raison :
le traduire ainsi créerait cycles et faux parents). Ces références ne deviennent pas des
arêtes une à une : elles sont traitées **en groupe** par ``version_chain``, qui trie la
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

VersionEntry = tuple[Mapping[str, Any], Identifier]
"""Une version identifiée : sa référence brute (datation, ``etat``) et son identifiant."""


def version_chain(
    entries: Sequence[VersionEntry], subject: LinkSubject
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
    if not entries:
        return []
    living = _living_sorted(entries)
    me = subject.current.serialize()
    position = next(
        (i for i, (_, ident) in enumerate(living) if ident.serialize() == me), None
    )
    if position is None:
        return _edge_if_stillborn(entries, living, subject)
    return _neighbour_edges(living, position, subject) + _stillborn_branches(
        entries, living, subject
    )


def _living_sorted(entries: Sequence[VersionEntry]) -> list[VersionEntry]:
    """Les versions entrées en vigueur, dans l'ordre du temps (``debut``, puis ``fin``)."""
    return sorted(
        (e for e in entries if not _is_stillborn(e[0])),
        key=lambda e: (str(e[0].get("debut", "")), str(e[0].get("fin", ""))),
    )


def _neighbour_edges(
    living: Sequence[VersionEntry], position: int, subject: LinkSubject
) -> list[Relation]:
    """« Ma version précédente → moi » et « moi → ma version suivante »."""
    relations: list[Relation] = []
    if position > 0:
        _, prev_id = living[position - 1]
        my_ref, _ = living[position]
        relations.append(
            subject.relation(prev_id, subject.current, SUCCEEDED_BY, _dating(my_ref))
        )
    if position < len(living) - 1:
        next_ref, next_id = living[position + 1]
        relations.append(
            subject.relation(subject.current, next_id, SUCCEEDED_BY, _dating(next_ref))
        )
    return relations


def _stillborn_branches(
    entries: Sequence[VersionEntry],
    living: Sequence[VersionEntry],
    subject: LinkSubject,
) -> list[Relation]:
    """Les mort-nées dont JE suis la version en vigueur au moment de l'avortement : ma
    branche latérale sortante."""
    me = subject.current.serialize()
    relations: list[Relation] = []
    for reference, identified in entries:
        if not _is_stillborn(reference):
            continue
        anchor = _anchor(living, str(reference.get("debut", "")))
        if anchor is not None and anchor[1].serialize() == me:
            relations.append(
                subject.relation(
                    subject.current, identified, SUCCEEDED_BY, _dating(reference)
                )
            )
    return relations


def _edge_if_stillborn(
    entries: Sequence[VersionEntry],
    living: Sequence[VersionEntry],
    subject: LinkSubject,
) -> list[Relation]:
    """JE suis peut-être une mort-née : mon arête entrante vient de la version vivante
    en vigueur au moment de l'avortement. Pas d'arête sortante — une version jamais née
    n'a pas de suite."""
    me = subject.current.serialize()
    mine = next(
        (r for r, ident in entries if ident.serialize() == me and _is_stillborn(r)),
        None,
    )
    if mine is None:
        return []
    anchor = _anchor(living, str(mine.get("debut", "")))
    if anchor is None:
        return []
    return [subject.relation(anchor[1], subject.current, SUCCEEDED_BY, _dating(mine))]


def _anchor(living: Sequence[VersionEntry], debut: str) -> VersionEntry | None:
    """La version en vigueur au moment de l'avortement d'une mort-née.

    C'est la dernière vivante dont le ``debut`` est STRICTEMENT antérieur au ``debut``
    théorique de la mort-née — laquelle partage précisément ce ``debut`` avec la version
    réelle qui l'a remplacée (mesuré : les 45 doublons de ``debut`` du corpus sont tous
    ce cas). Un tri qui les confondrait est exactement ce que la branche latérale évite.
    """
    candidates = [e for e in living if str(e[0].get("debut", "")) < debut]
    return candidates[-1] if candidates else None


def _dating(reference: Mapping[str, Any]) -> dict[str, Any]:
    """La datation d'une version, extraite de sa référence — elle finit sur l'arête.

    C'est elle qui rend la ligne de vie lisible dans le graphe (``debut``/``fin``/
    ``etat``/``num``), et c'est l'``etat`` qui permet d'écarter les mort-nées d'une
    requête sans casser la chaîne.
    """
    return {k: v for k, v in reference.items() if k not in ("kind", "id")}


def _is_stillborn(reference: Mapping[str, Any]) -> bool:
    return str(reference.get("etat", "")).endswith(STILLBORN_SUFFIX)
