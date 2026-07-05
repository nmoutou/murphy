"""Régression : vérifier que ``LegiRelationExtractor._reduce`` applique bien
la réduction transitive (NetworkX) sur un DAG ``A → B → C, A → C`` et conserve
les arêtes inchangées sur un graphe contenant un cycle.
"""

from ragcore.core.models import DocumentId, OwnerId, Relation, RelationType, SourceName
from ragcore.sources.legi.relations import LegiRelationExtractor

OWNER = OwnerId("u1")
A = DocumentId("LEGIARTI000000000001")
B = DocumentId("LEGIARTI000000000002")
C = DocumentId("LEGIARTI000000000003")


def _rel(src: DocumentId, tgt: DocumentId, rtype: RelationType = RelationType.CITES) -> Relation:
    return Relation(
        source_document_id=src,
        target_document_id=tgt,
        relation_type=rtype,
        owner_id=OWNER,
        source=SourceName.LEGI,
    )


def test_reduce_drops_redundant_transitive_edge() -> None:
    extractor = LegiRelationExtractor()
    relations = [_rel(A, B), _rel(B, C), _rel(A, C)]
    result = extractor._reduce(relations)

    edges = {(r.source_document_id, r.target_document_id) for r in result}
    assert (A, B) in edges
    assert (B, C) in edges
    assert (A, C) not in edges  # éliminé par la réduction transitive


def test_reduce_preserves_cycles() -> None:
    """Si le graphe contient un cycle, la réduction est skippée pour ce sous-graphe."""
    extractor = LegiRelationExtractor()
    relations = [_rel(A, B), _rel(B, A)]
    result = extractor._reduce(relations)

    edges = {(r.source_document_id, r.target_document_id) for r in result}
    assert (A, B) in edges
    assert (B, A) in edges


def test_reduce_isolates_per_relation_type() -> None:
    """Une relation ``cites`` et une relation ``modifies`` ne sont jamais fusionnées."""
    extractor = LegiRelationExtractor()
    relations = [
        _rel(A, B, RelationType.CITES),
        _rel(B, C, RelationType.CITES),
        _rel(A, C, RelationType.MODIFIES),
    ]
    result = extractor._reduce(relations)

    typed = {(r.source_document_id, r.target_document_id, r.relation_type) for r in result}
    assert (A, B, RelationType.CITES) in typed
    assert (B, C, RelationType.CITES) in typed
    # La relation MODIFIES n'est pas affectée par le DAG CITES
    assert (A, C, RelationType.MODIFIES) in typed


def test_reduce_empty_returns_empty() -> None:
    extractor = LegiRelationExtractor()
    assert extractor._reduce([]) == []
