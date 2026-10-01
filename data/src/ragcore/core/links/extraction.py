"""La face EXTRACTION de ``core/links`` : une balise brute devient une arête.

**Le module hégémonique, et ce que ça veut dire.** Un seul module au cœur définit tout
ce qui touche aux liens. Il a deux faces : *extraction* (ici — appelée par le parser) et
*résolution* (la passe de phase 2). Elles partagent le vocabulaire de ``vocabulary.py``.
**Personne d'autre ne fabrique de lien.** ``sources/legislatif/relations.py`` en fabriquait un,
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
"""Le ``kind`` des références produites par la CASCADE du parser.

Une balise NON-CONFIGURÉE dont la valeur a la forme d'un identifiant DILA (et n'est pas
le document lui-même) est une donnée qui *pointe* : elle passe la porte « liens », pas
la porte « metadata ». Le parser l'émet sous ce kind — sans ``typelien`` ni ``sens``,
puisque la source n'a rien déclaré — et le domaine la traduit ici en arête
``references``, du document courant VERS la cible. Le verbe générique est assumé : on
sait QUE ça pointe, pas POURQUOI ; le jour où la table apprend la balise, elle prendra
un rôle déclaré et un verbe précis.
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
    """Les types de lien non-configurés (catégorie ``links``) : les ``typelien`` que la
    table ne traduit pas. Les liens heuristiques, eux, sont signalés au parse, où leur
    clé chemin-complet est connue."""

    unconfigured_relations: list[Relation] = field(default_factory=list)
    """Les arêtes d'un type de lien NON-CONFIGURÉ (ADR-048) : heuristiques, ou d'un
    ``typelien`` inconnu. Séparées de ``relations`` pour que le curseur
    ``skip_unconfigured`` puisse les retirer sans que l'extraction le connaisse."""

    lost_links: int = 0
    """Les liens que la source a écrits mais qu'on ne sait pas écrire : ``sens``
    inconnu, ``@id`` illisible, ``typelien`` qui ne peut pas être un verbe. Ils ne
    deviennent pas des arêtes ; ce compte est ce qui les empêche de disparaître en
    silence (``relation.unknown``)."""

    unformatted_relations: list[UnformattedRelation] = field(default_factory=list)
    """Les cibles DÉCRITES — celles dont l'``@id`` était vide.

    Elles ne sont pas des arêtes et n'en produiront aucune : elles rejoignent la
    collection ``unformatted_relations``. Voir ``core.models.unformatted_relation``.
    """


def extract_links(
    references: Sequence[Mapping[str, Any]],
    ancestors: Sequence[Mapping[str, Any]],
    table: LinkTable,
    subject: LinkSubject,
) -> ExtractedLinks:
    """Traduit les liens relevés par le parser en arêtes du domaine.

    Le parser a déjà fait son travail : il a relevé les ``<LIEN>`` **bruts** (avec le
    vocabulaire de la source : ``typelien``, ``sens``, ``id``) et les ancêtres. Il ne les
    a pas typés — le faire aurait mis la table de traduction dans deux modules à la fois.

    Ici, le domaine traduit. Ce qu'il ne sait pas traduire, il l'INGÈRE SOUS SON NOM BRUT
    et le déclare. Il ne le jette pas. Ce qu'il ne sait pas écrire, il le compte.
    """
    extraction = _Extraction(table=table, subject=subject)
    unformatted_relations: list[UnformattedRelation] = []

    # Les liens de VERSION se traitent EN GROUPE (cf. `versions.py`) : la chaîne est une
    # propriété de la liste, pas de chaque lien pris isolément.
    versions = [r for r in references if r.get("kind", "") == VERSION_KIND]
    relations = version_chain(extraction.identified(versions), subject)

    for reference in references:
        if reference.get("kind", "") == VERSION_KIND:
            continue
        extracted = extraction.from_reference(reference)
        # Deux natures, un seul aiguillage — l'identification de la cible. Le `match`
        # dit lequel des deux plans reçoit la balise : le graphe, ou les relations non
        # formatées. `None` : rien pour ces deux plans — un lien perdu, ou une arête
        # non-configurée, que `_Extraction` a déjà rangée à part.
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
    """L'extraction des liens d'UN document : sa table, son sujet, et ce qu'elle range à
    part — ses inconnus, ses arêtes non-configurées, ses liens perdus.

    Ils voyagent ensemble d'une balise à l'autre ; les porter une fois évite de les
    repasser à chaque étape de la cascade.
    """

    table: LinkTable
    subject: LinkSubject
    unknowns: dict[str, list[str]] = field(default_factory=dict)
    unconfigured: list[Relation] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)
    """La valeur fautive de chaque lien perdu — seul son nombre sort."""

    def identified(self, references: Sequence[Mapping[str, Any]]) -> list[VersionEntry]:
        """Les références dont la cible s'identifie, avec leur identifiant."""
        return [
            (reference, identified)
            for reference in references
            if (identified := self.identifier(reference.get("id", ""))) is not None
        ]

    def from_reference(
        self, reference: Mapping[str, Any]
    ) -> Relation | UnformattedRelation | None:
        """Une balise brute devient une ARÊTE si sa cible est identifiée, une RELATION
        NON FORMATÉE sinon.

        L'``@id`` est le seul aiguillage. Ce qui est identifié rejoint le graphe ; ce qui
        est seulement décrit rejoint les relations non formatées. Rien n'est jeté au passage — c'était le
        défaut de la version précédente, qui perdait 89 liens LEGI sans le dire.
        """
        kind = reference.get("kind", "")
        if kind == HEURISTIC_KIND:
            self._heuristic(reference)
            return None

        linked = self.identifier(reference.get("id", ""))
        if linked is None:
            # Pas d'identifiant : la cible est DÉCRITE (`unformatted_relation_from`), ou
            # elle n'est rien — ni identifiant, ni texte. La déclarer en `unknowns`
            # polluerait alors le bilan avec un mot qui n'existe pas.
            return unformatted_relation_from(reference, self.table, self.subject)

        if kind in self.table.structural_kinds:
            # Orientation par construction : le document courant CONTIENT le lié.
            return self.subject.relation(
                self.subject.current, linked, CONTAINS, {"kind": kind}
            )
        return self._typed(reference, linked)

    def _heuristic(self, reference: Mapping[str, Any]) -> None:
        """La cascade du parser a reconnu une valeur au format DILA sur une balise
        non-configurée.

        Pas de `typelien`, pas de `sens` : la source n'a rien déclaré. Orientation par
        construction (le document courant PORTE la référence), verbe générique
        `references`. La balise d'origine survit en métadonnée d'arête — c'est elle qui
        dira, plus tard, quoi apprendre à la table. L'arête est NON-CONFIGURÉE : elle va
        à part, là où le curseur peut la retirer.
        """
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
        """Un lien déclaré par la source : son `typelien` donne le verbe, son `sens`
        l'orientation."""
        raw_typelien = reference.get("typelien", "")
        relation_verb, known = translate(self.table.translation, raw_typelien)

        if relation_verb is None:
            # Le mot ne peut pas ÊTRE un verbe (vide, caractères interdits) : il n'y a
            # rien à écrire dans le graphe, et ce n'est pas un type de lien. Le lien est
            # perdu, et compté.
            self.lost.append(raw_typelien)
            return None

        if not known:
            # Le verbe entre dans le graphe SOUS SON NOM BRUT, et le fait est déclaré.
            declare_unknown(self.unknowns, CATEGORY_LINK, raw_typelien)

        raw_sens = reference.get("sens", "")
        oriented = orient(self.subject.current, linked, raw_sens)
        if oriented is None:
            # Une arête qu'on ne sait pas orienter, on ne l'écrit pas au hasard : un
            # graphe faux ne se distingue pas d'un graphe vrai. On compte le lien perdu.
            self.lost.append(raw_sens)
            return None

        edge_source, edge_target = oriented
        relation = self.subject.relation(
            edge_source,
            edge_target,
            relation_verb,
            # Le vocabulaire d'origine SURVIT — même quand il a été traduit.
            # `references` recouvre neuf `typelien` distincts : sans cette trace,
            # « CODIFICATION » et « CONCORDANCE » deviendraient indiscernables une fois
            # en base.
            {"typelien": raw_typelien, "sens": raw_sens},
        )
        if known:
            return relation
        # Un `typelien` inconnu est un type de lien NON-CONFIGURÉ : l'arête va à part.
        self.unconfigured.append(relation)
        return None

    def from_ancestor(self, ancestor: Mapping[str, Any]) -> Relation | None:
        """L'ancêtre CONTIENT le document courant. Orientation fixe, jamais ambiguë."""
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
            # `@id` vide : une ABSENCE, pas un inconnu.
            return None
        try:
            return Identifier(raw=raw_id)
        except PydanticValidationError:
            # `@id` présent mais illisible : la source a écrit une référence qu'on ne
            # sait pas transformer. La taire ferait disparaître l'arête en silence ; on
            # la COMPTE, pour que le bilan la porte (`relation.unknown`).
            self.lost.append(raw_id)
            return None
