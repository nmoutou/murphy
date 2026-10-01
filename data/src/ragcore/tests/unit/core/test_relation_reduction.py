"""La réduction transitive, et surtout ce qu'elle ne doit pas toucher : les
citations."""

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
    """``<CONTEXTE>`` déclare la fermeture, ``<STRUCTURE_TA>`` l'arbre : l'union réduite
    redonne l'arbre A⊃B⊃C, sans le raccourci A⊃C."""
    result = reduce_transitively([_rel(A, B), _rel(B, C), _rel(A, C)])

    assert _edges(result) == {
        (A.raw, B.raw, CONTAINS),
        (B.raw, C.raw, CONTAINS),
    }


def test_les_citations_ne_sont_JAMAIS_reduites() -> None:
    """« A cite B, B cite C, A cite C » : trois citations réelles, aucune ne tombe."""
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
        (A.raw, C.raw, CITES),  # celle qu'une réduction naïve effacerait
    }


def test_un_cycle_est_conserve_tel_quel() -> None:
    """Un cycle de contenance n'est pas réductible : il est laissé visible."""
    result = reduce_transitively([_rel(A, B), _rel(B, A)])

    assert _edges(result) == {
        (A.raw, B.raw, CONTAINS),
        (B.raw, A.raw, CONTAINS),
    }


def test_les_types_ne_se_melangent_pas() -> None:
    """Chaque verbe a son graphe : une contenance A⊃B⊃C n'efface pas la citation A→C."""
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
    """networkx ne rend que des couples de chaînes : les métadonnées, dont le
    ``typelien`` d'origine, doivent survivre."""
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
