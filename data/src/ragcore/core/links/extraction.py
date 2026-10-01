"""L'extraction : une balise brute devient une arête.

La source apporte une ``LinkTable`` ; le domaine garde la mécanique (lire les attributs,
orienter, fabriquer la ``Relation``, déclarer ce qu'il n'a pas su nommer). Une source
nouvelle écrit une table, pas un extracteur.

Aucune arête n'est produite seulement quand il n'y a rien à écrire : pas d'identifiant
cible, ou un mot qui ne peut pas être un verbe.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ..models.identifiers import Identifier
from ..models.relation import Relation
from ..models.unformatted_relation import UnformattedRelation
from ..services.unknown_categories import CATEGORY_LINK, declare_unknown
from .orientation import orient
from .subject import LinkSubject
from .table import LinkTable
from .unformatted import unformatted_relation_from
from .versions import STILLBORN_SUFFIX, VERSION_KIND, VersionEntry, version_chain
from .vocabulary import CONTAINS, REFERENCES, translate

__all__ = [
    "HEURISTIC_KIND",
    "STILLBORN_SUFFIX",
    "VERSION_KIND",
    "ExtractedLinks",
    "LinkSubject",
    "LinkTable",
    "UnformattedRelation",
    "extract_links",
]


HEURISTIC_KIND = "unconfigured:dila_id"
"""Le ``kind`` des références trouvées par la cascade du parser : une balise non
configurée dont la valeur a la forme d'un identifiant DILA. Elle devient une arête
``references`` du document courant vers la cible : on sait que ça pointe, pas pourquoi.
"""


@dataclass(frozen=True)
class ExtractedLinks:
    """Ce que l'extraction a produit, et ce qu'elle n'a pas su nommer : l'appelant
    déclarera les inconnus à la télémétrie.
    """

    relations: list[Relation] = field(default_factory=list)
    unknowns: dict[str, list[str]] = field(default_factory=dict)
    """Les ``typelien`` que la table ne traduit pas. Les liens heuristiques sont signalés
    au parse, où leur clé chemin-complet est connue."""

    unconfigured_relations: list[Relation] = field(default_factory=list)
    """Arêtes heuristiques ou de ``typelien`` inconnu (ADR-048), à part pour que
    ``skip_unconfigured`` puisse les retirer sans que l'extraction le connaisse."""

    lost_links: int = 0
    """Liens de la source qu'on ne sait pas écrire (``sens`` inconnu, ``@id`` illisible,
    ``typelien`` impossible en verbe), comptés en ``relation.unknown``."""

    unformatted_relations: list[UnformattedRelation] = field(default_factory=list)
    """Les cibles décrites, à ``@id`` vide : pas des arêtes."""


def extract_links(
    references: Sequence[Mapping[str, Any]],
    ancestors: Sequence[Mapping[str, Any]],
    table: LinkTable,
    subject: LinkSubject,
) -> ExtractedLinks:
    """Le parser relève les ``<LIEN>`` bruts, sans les typer ; le domaine traduit ici.
    Ce qu'il ne sait pas traduire entre sous son nom brut ; ce qu'il ne sait pas écrire
    est compté.
    """
    extraction = _Extraction(table=table, subject=subject)
    unformatted_relations: list[UnformattedRelation] = []

    # Les liens de version se traitent en groupe : la chaîne est une propriété de la
    # liste, pas de chaque lien.
    versions = [r for r in references if r.get("kind", "") == VERSION_KIND]
    relations = version_chain(extraction.identified(versions), subject)

    for reference in references:
        if reference.get("kind", "") == VERSION_KIND:
            continue
        extracted = extraction.from_reference(reference)
        # `None` : lien perdu, ou arête non configurée déjà rangée à part
        match extracted:
            case Relation():
                relations.append(extracted)
            case UnformattedRelation():
                unformatted_relations.append(extracted)
            case None:
                pass

    relations.extend(
        relation
        for ancestor in ancestors
        if (relation := extraction.from_ancestor(ancestor)) is not None
    )
    return ExtractedLinks(
        relations=relations,
        unknowns=extraction.unknowns,
        unconfigured_relations=extraction.unconfigured,
        lost_links=len(extraction.lost),
        unformatted_relations=unformatted_relations,
    )


@dataclass(frozen=True)
class _Extraction:
    """L'extraction des liens d'un document, et ce qu'elle range à part."""

    table: LinkTable
    subject: LinkSubject
    unknowns: dict[str, list[str]] = field(default_factory=dict)
    unconfigured: list[Relation] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)
    """La valeur fautive de chaque lien perdu ; seul leur nombre sort."""

    def identified(self, references: Sequence[Mapping[str, Any]]) -> list[VersionEntry]:
        return [
            (reference, identified)
            for reference in references
            if (identified := self.identifier(reference.get("id", ""))) is not None
        ]

    def from_reference(
        self, reference: Mapping[str, Any]
    ) -> Relation | UnformattedRelation | None:
        """Une arête si l'``@id`` identifie la cible, une relation non formatée sinon."""
        kind = reference.get("kind", "")
        if kind == HEURISTIC_KIND:
            self._heuristic(reference)
            return None

        linked = self.identifier(reference.get("id", ""))
        if linked is None:
            return unformatted_relation_from(reference, self.table, self.subject)

        if kind in self.table.structural_kinds:
            return self.subject.relation(
                self.subject.current, linked, CONTAINS, {"kind": kind}
            )
        return self._typed(reference, linked)

    def _heuristic(self, reference: Mapping[str, Any]) -> None:
        """La balise d'origine survit en métadonnée d'arête : elle dira quoi apprendre à
        la table."""
        linked = self.identifier(reference.get("id", ""))
        if linked is None:
            return
        self.unconfigured.append(
            self.subject.relation(
                self.subject.current,
                linked,
                REFERENCES,
                {"kind": reference.get("tag", ""), "origin": "heuristic"},
            )
        )

    def _typed(
        self, reference: Mapping[str, Any], linked: Identifier
    ) -> Relation | None:
        raw_typelien = reference.get("typelien", "")
        relation_verb, known = translate(self.table.translation, raw_typelien)

        if relation_verb is None:
            self.lost.append(raw_typelien)
            return None

        if not known:
            declare_unknown(self.unknowns, CATEGORY_LINK, raw_typelien)

        raw_sens = reference.get("sens", "")
        oriented = orient(self.subject.current, linked, raw_sens)
        if oriented is None:
            # Jamais orientée au hasard : un graphe faux ne se distingue pas d'un vrai
            self.lost.append(raw_sens)
            return None

        edge_source, edge_target = oriented
        relation = self.subject.relation(
            edge_source,
            edge_target,
            relation_verb,
            # Même traduit, le `typelien` d'origine survit : `references` en recouvre
            # plusieurs, indiscernables sans cette trace.
            {"typelien": raw_typelien, "sens": raw_sens},
        )
        if known:
            return relation
        self.unconfigured.append(relation)
        return None

    def from_ancestor(self, ancestor: Mapping[str, Any]) -> Relation | None:
        """L'ancêtre contient le document courant."""
        if ancestor.get("kind") not in self.table.ancestor_kinds:
            return None
        linked = self.identifier(ancestor.get("id", ""))
        if linked is None:
            return None
        return self.subject.relation(
            linked, self.subject.current, CONTAINS, {"kind": ancestor.get("kind", "")}
        )

    def identifier(self, raw_id: str) -> Identifier | None:
        if not raw_id:
            return None
        try:
            return Identifier(raw=raw_id)
        except PydanticValidationError:
            # `@id` illisible : compté, pour ne pas disparaître en silence
            self.lost.append(raw_id)
            return None
