"""La réduction transitive — et surtout : ce qu'elle NE doit PAS toucher.

Ces tests reprennent la spécification que portaient les trois ``xfail`` de
``sources/legislatif/tests/test_relation_reduction.py``. Ceux-là testaient une méthode
privée (``LegiRelationExtractor._reduce``) : le sujet a déménagé dans le domaine,
les tests l'ont suivi. Leur fichier annonçait lui-même « à réécrire au lot 4 ».

S'y ajoute le test qu'ils ne POUVAIENT pas contenir, parce qu'il contredit ce
qu'ils tenaient pour acquis : la réduction n'a aucune légitimité sur une citation.
"""

from ragcore.core.links import CITES, CONTAINS
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.relation import Relation
from ragcore.core.services.relation_reduction import reduce_transitively

A = Identifier(raw="LEGIARTI000000000001")
B = Identifier(raw="LEGIARTI000000000002")
C = Identifier(raw="LEGIARTI000000000003")


def _rel(src: Identifier, tgt: Identifier, rtype: str = CONTAINS) -> Relation:
    return Relation(
        source_identifier=src,
        target_identifier=tgt,
        relation_type=rtype,
        source=SourceName.LEGI,
    )


def _edges(relations: list[Relation]) -> set[tuple[str, str, str]]:
    return {
        (r.source_identifier.raw, r.target_identifier.raw, r.relation_type)
        for r in relations
    }


def test_la_fermeture_transitive_est_reduite_en_arbre() -> None:
    """C'est le cas réel : ``<CONTEXTE>`` déclare A⊃B, A⊃C et B⊃C (la fermeture),
    ``<STRUCTURE_TA>`` déclare l'arbre. L'union est la fermeture ; la réduire la
    ramène à l'arbre A⊃B⊃C. L'arête directe A⊃C n'apporte rien : le chemin la dit.
    """
    result = reduce_transitively([_rel(A, B), _rel(B, C), _rel(A, C)])

    assert _edges(result) == {
        (A.raw, B.raw, CONTAINS),
        (B.raw, C.raw, CONTAINS),
    }


def test_les_citations_ne_sont_JAMAIS_reduites() -> None:
    """LE test du lot. « A cite B, B cite C, A cite C » : trois citations RÉELLES.

    Supprimer A→C parce qu'un chemin existe, ce serait décréter que citer un texte
    revient à citer tout ce qu'il cite. Le graphe mentirait sur ce que les textes
    déclarent. C'est ce que faisait l'ancien ``_reduce``, sur les 14 326 CITATION du
    corpus.
    """
    result = reduce_transitively(
        [
            _rel(A, B, CITES),
            _rel(B, C, CITES),
            _rel(A, C, CITES),
        ]
    )

    assert _edges(result) == {
        (A.raw, B.raw, CITES),
        (B.raw, C.raw, CITES),
        (A.raw, C.raw, CITES),  # ← l'arête que la réduction effaçait
    }


def test_un_cycle_est_conserve_tel_quel() -> None:
    """La réduction transitive n'est définie que sur les DAG. Un cycle de contenance
    est une anomalie du corpus : on ne la corrige pas, et surtout on ne la cache pas.
    """
    result = reduce_transitively([_rel(A, B), _rel(B, A)])

    assert _edges(result) == {
        (A.raw, B.raw, CONTAINS),
        (B.raw, A.raw, CONTAINS),
    }


def test_les_types_ne_se_melangent_pas() -> None:
    """Une contenance et une citation ne partagent pas de graphe. Sans ce cloisonnement,
    la chaîne de contenance A⊃B⊃C ferait disparaître une citation A→C — un type
    effacerait les arêtes d'un autre.
    """
    result = reduce_transitively(
        [
            _rel(A, B, CONTAINS),
            _rel(B, C, CONTAINS),
            _rel(A, C, CONTAINS),  # réductible : elle tombe
            _rel(A, C, CITES),  # autre type : elle reste
        ]
    )

    assert _edges(result) == {
        (A.raw, B.raw, CONTAINS),
        (B.raw, C.raw, CONTAINS),
        (A.raw, C.raw, CITES),
    }


def test_le_typelien_dorigine_survit_a_la_reduction() -> None:
    """networkx ne rend que des couples de chaînes : les métadonnées ne sont pas dans
    le graphe. Si la réduction les perdait, elle effacerait le vocabulaire d'origine
    (``metadata["typelien"]``) — l'information même qu'on a pris soin de ne pas jeter.
    """
    relation = Relation(
        source_identifier=A,
        target_identifier=B,
        relation_type=CONTAINS,
        source=SourceName.LEGI,
        metadata={"typelien": "LIEN_ART"},
    )

    (survivor,) = reduce_transitively([relation])

    assert survivor.metadata == {"typelien": "LIEN_ART"}


def test_reduire_le_vide_rend_le_vide() -> None:
    assert reduce_transitively([]) == []
