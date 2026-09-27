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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ..models.citation import Citation
from ..models.identifiers import SourceIdentifier
from ..models.relation import Relation
from ..services.unknown_categories import (
    CATEGORY_IDENTIFIER,
    CATEGORY_SENS,
    CATEGORY_TYPELIEN,
    declare_unknown,
)
from .citations import citation_from
from .subject import LinkSubject
from .table import LinkTable
from .versions import STILLBORN_SUFFIX, VERSION_KIND, VersionEntry, version_chain
from .vocabulary import CONTAINS, REFERENCES, translate

__all__ = [
    "HEURISTIC_KIND",
    "STILLBORN_SUFFIX",
    "VERSION_KIND",
    "Citation",
    "ExtractedLinks",
    "LinkSubject",
    "LinkTable",
    "extract_links",
]


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
    et le déclare. Il ne le jette pas.
    """
    extraction = _Extraction(table=table, subject=subject, unknowns={})
    citations: list[Citation] = []

    # Les liens de VERSION se traitent EN GROUPE (cf. `versions.py`) : la chaîne est une
    # propriété de la liste, pas de chaque lien pris isolément.
    versions = [r for r in references if r.get("kind", "") == VERSION_KIND]
    relations = version_chain(extraction.identified(versions), subject)

    for reference in references:
        if reference.get("kind", "") == VERSION_KIND:
            continue
        extracted = extraction.from_reference(reference)
        # Deux natures, un seul aiguillage — l'identification de la cible. Le `match`
        # dit lequel des deux plans reçoit la balise : le graphe, ou le document.
        match extracted:
            case Relation():
                relations.append(extracted)
            case Citation():
                citations.append(extracted)
            case None:
                pass

    relations.extend(
        relation
        for ancestor in ancestors
        if (relation := extraction.from_ancestor(ancestor)) is not None
    )
    return ExtractedLinks(
        relations=relations, unknowns=extraction.unknowns, citations=citations
    )


@dataclass(frozen=True)
class _Extraction:
    """L'extraction des liens d'UN document : sa table, son sujet, ses inconnus.

    Ces trois-là voyagent ensemble d'une balise à l'autre ; les porter une fois évite de
    les repasser à chaque étape de la cascade.
    """

    table: LinkTable
    subject: LinkSubject
    unknowns: dict[str, list[str]]

    def identified(self, references: Sequence[Mapping[str, Any]]) -> list[VersionEntry]:
        """Les références dont la cible s'identifie, avec leur identifiant."""
        return [
            (reference, identified)
            for reference in references
            if (identified := self.identifier(reference.get("id", ""))) is not None
        ]

    def from_reference(
        self, reference: Mapping[str, Any]
    ) -> Relation | Citation | None:
        """Une balise brute devient une ARÊTE si sa cible est identifiée, une CITATION
        sinon.

        L'``@id`` est le seul aiguillage. Ce qui est identifié rejoint le graphe ; ce qui
        est seulement décrit rejoint le document. Rien n'est jeté au passage — c'était le
        défaut de la version précédente, qui perdait 89 liens LEGI sans le dire.
        """
        kind = reference.get("kind", "")
        if kind == HEURISTIC_KIND:
            return self._heuristic(reference)

        linked = self.identifier(reference.get("id", ""))
        if linked is None:
            # Pas d'identifiant : la cible est DÉCRITE (`citation_from`), ou elle n'est
            # rien — ni identifiant, ni texte. La déclarer en `unknowns` polluerait alors
            # le bilan avec un mot qui n'existe pas.
            return citation_from(reference, self.table)

        if kind in self.table.structural_kinds:
            # Orientation par construction : le document courant CONTIENT le lié.
            return self.subject.relation(
                self.subject.current, linked, CONTAINS, {"kind": kind}
            )
        return self._typed(reference, linked)

    def _heuristic(self, reference: Mapping[str, Any]) -> Relation | None:
        """La cascade du parser a reconnu une valeur au format DILA sur une balise
        non-configurée.

        Pas de `typelien`, pas de `sens` : la source n'a rien déclaré. Orientation par
        construction (le document courant PORTE la référence), verbe générique
        `references`. La balise d'origine survit en métadonnée d'arête — c'est elle qui
        dira, plus tard, quoi apprendre à la table.
        """
        linked = self.identifier(reference.get("id", ""))
        if linked is None:
            return None
        return self.subject.relation(
            self.subject.current,
            linked,
            REFERENCES,
            {"kind": reference.get("tag", ""), "origin": "heuristic"},
        )

    def _typed(
        self, reference: Mapping[str, Any], linked: SourceIdentifier
    ) -> Relation | None:
        """Un lien déclaré par la source : son `typelien` donne le verbe, son `sens`
        l'orientation."""
        raw_typelien = reference.get("typelien", "")
        relation_verb, known = translate(self.table.translation, raw_typelien)

        if relation_verb is None:
            # Le mot ne peut pas ÊTRE un verbe (vide, caractères interdits) : il n'y a
            # rien à écrire dans le graphe. Ce n'est pas un renoncement — c'est
            # l'absence de mot.
            declare_unknown(self.unknowns, CATEGORY_TYPELIEN, raw_typelien or "<vide>")
            return None

        if not known:
            # Le verbe entre dans le graphe SOUS SON NOM BRUT, et le fait est déclaré.
            # L'arête existe : c'est là toute la différence avec la version qu'on
            # remplace.
            declare_unknown(self.unknowns, CATEGORY_TYPELIEN, raw_typelien)

        raw_sens = reference.get("sens", "")
        oriented = _orient(self.subject.current, linked, raw_sens)
        if oriented is None:
            # Une arête qu'on ne sait pas orienter, on ne l'écrit pas au hasard : un
            # graphe faux ne se distingue pas d'un graphe vrai. On dit qu'on n'a pas su.
            declare_unknown(self.unknowns, CATEGORY_SENS, raw_sens or "<vide>")
            return None

        edge_source, edge_target = oriented
        return self.subject.relation(
            edge_source,
            edge_target,
            relation_verb,
            # Le vocabulaire d'origine SURVIT — même quand il a été traduit.
            # `references` recouvre neuf `typelien` distincts : sans cette trace,
            # « CODIFICATION » et « CONCORDANCE » deviendraient indiscernables une fois
            # en base.
            {"typelien": raw_typelien, "sens": raw_sens},
        )

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

    def identifier(self, raw_id: str) -> SourceIdentifier | None:
        if not raw_id or self.table.identifier_for is None:
            # `@id` vide ou source qui n'identifie pas : une ABSENCE, pas un inconnu.
            return None
        try:
            return self.table.identifier_for(raw_id)
        except PydanticValidationError:
            # `@id` présent mais illisible : la source a écrit une référence qu'on ne
            # sait pas transformer. La taire ferait disparaître l'arête en silence ; on
            # la DÉCLARE, pour que le bilan la porte et que la table apprenne. Toute
            # autre exception est un bug de la table, pas un défaut du corpus : elle
            # remonte.
            declare_unknown(self.unknowns, CATEGORY_IDENTIFIER, raw_id)
            return None


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
