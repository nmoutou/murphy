"""La chaîne temporelle des versions d'un document.

Les liens de version se traitent en groupe : traduits un à un, ils donneraient le
produit cartésien des versions au lieu de leur chaîne.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..models.identifiers import Identifier
from ..models.relation import Relation
from .subject import LinkSubject
from .vocabulary import SUIVI_PAR

__all__ = ["STILLBORN_SUFFIX", "VERSION_KIND", "VersionEntry", "version_chain"]


VERSION_KIND = "version:lien"
"""Chaque ``<LIEN_ART>`` d'un bloc ``<VERSIONS>`` désigne une version datée du même
article, jamais une contenance : en faire une créerait cycles et faux parents.
"""

STILLBORN_SUFFIX = "_MORT_NE"
"""Le marqueur DILA d'une version jamais entrée en vigueur (``MODIFIE_MORT_NE``…).

Le critère fiable est ce suffixe, pas les dates : 12 liens mort-nés sur 57 ont des
dates d'apparence normale.
"""

VersionEntry = tuple[Mapping[str, Any], Identifier]
"""La référence brute (datation, ``etat``) et l'identifiant d'une version."""


def version_chain(
    entries: Sequence[VersionEntry], subject: LinkSubject
) -> list[Relation]:
    """Chaque version pointe sa suivante, dans le sens du temps.

    Le document courant n'émet que les arêtes qui le touchent, entrante et sortante :
    chaque arête est émise par ses deux bouts et le ``MERGE`` dédoublonne, donc la
    chaîne survit à un maillon absent du corpus.

    L'auto-référence (le bloc ``<VERSIONS>`` liste l'article lui-même) est l'ancre qui
    localise le document dans la liste triée ; sans elle, rien à émettre.

    Les mort-nées sont hors chaîne, jamais applicables : elles s'accrochent en branche
    latérale à la version en vigueur au moment de l'avortement.
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
    return sorted(
        (e for e in entries if not _is_stillborn(e[0])),
        key=lambda e: (str(e[0].get("debut", "")), str(e[0].get("fin", ""))),
    )


def _neighbour_edges(
    living: Sequence[VersionEntry], position: int, subject: LinkSubject
) -> list[Relation]:
    relations: list[Relation] = []
    if position > 0:
        _, prev_id = living[position - 1]
        my_ref, _ = living[position]
        relations.append(
            subject.relation(prev_id, subject.current, SUIVI_PAR, _dating(my_ref))
        )
    if position < len(living) - 1:
        next_ref, next_id = living[position + 1]
        relations.append(
            subject.relation(subject.current, next_id, SUIVI_PAR, _dating(next_ref))
        )
    return relations


def _stillborn_branches(
    entries: Sequence[VersionEntry],
    living: Sequence[VersionEntry],
    subject: LinkSubject,
) -> list[Relation]:
    """Les mort-nées dont le document courant était la version en vigueur à
    l'avortement."""
    me = subject.current.serialize()
    relations: list[Relation] = []
    for reference, identified in entries:
        if not _is_stillborn(reference):
            continue
        anchor = _anchor(living, str(reference.get("debut", "")))
        if anchor is not None and anchor[1].serialize() == me:
            relations.append(
                subject.relation(
                    subject.current, identified, SUIVI_PAR, _dating(reference)
                )
            )
    return relations


def _edge_if_stillborn(
    entries: Sequence[VersionEntry],
    living: Sequence[VersionEntry],
    subject: LinkSubject,
) -> list[Relation]:
    """Si le document courant est mort-né, son arête entrante vient de la version en
    vigueur à l'avortement ; aucune sortante, une version jamais née n'a pas de suite."""
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
    return [subject.relation(anchor[1], subject.current, SUIVI_PAR, _dating(mine))]


def _anchor(living: Sequence[VersionEntry], debut: str) -> VersionEntry | None:
    """La dernière version vivante dont le ``debut`` est strictement antérieur à celui
    de la mort-née : elle partage souvent ce ``debut`` avec la version qui l'a remplacée.
    """
    candidates = [e for e in living if str(e[0].get("debut", "")) < debut]
    return candidates[-1] if candidates else None


def _dating(reference: Mapping[str, Any]) -> dict[str, Any]:
    """Finit sur l'arête : son ``etat`` permet d'écarter les mort-nées d'une requête."""
    return {k: v for k, v in reference.items() if k not in ("kind", "id")}


def _is_stillborn(reference: Mapping[str, Any]) -> bool:
    return str(reference.get("etat", "")).endswith(STILLBORN_SUFFIX)
