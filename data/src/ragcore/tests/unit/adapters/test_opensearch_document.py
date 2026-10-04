"""Le corps d'un document OpenSearch, et la définition de l'index qu'il doit respecter.
Ce qu'OpenSearch en fait (mapping strict, dates, remplacement) se prouve en intégration.
"""

from typing import Any

import pytest

from ragcore.adapters.storage.opensearch.index_document import build_index_document
from ragcore.adapters.storage.opensearch.search_index import (
    _load_index_definition,
    check_vector_dimension,
)
from ragcore.core.models.chunk import Chunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.search_content import IndexedPassage, SearchContent

IDENTIFIER = Identifier(raw="LEGIARTI000045938851")
DECREE = "Décret n° 2005-850 du 27 juillet 2005 relatif aux délégations de signature"
DECREE_VARIANT = "Décret n°2005-850 du 27 juillet 2005 relatif aux délégations."


def _doc(
    context: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ParsedDocument:
    return ParsedDocument(
        identifier=IDENTIFIER,
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title="3",
        content="Le passage indexé.",
        structure={"context": context or []},
        metadata=metadata or {},
    )


def _passage(embedding: list[float] | None) -> IndexedPassage:
    return IndexedPassage(
        chunk=Chunk(
            chunk_id="LEGIARTI000045938851_0000",
            parent_identifier=IDENTIFIER,
            document_type=DocumentType.ARTICLE,
            ordinal=0,
            text="Le passage indexé.",
            tag_path=[],
            char_start=0,
            char_end=18,
        ),
        embedding=embedding,
    )


def _title(kind: str, label: str) -> dict[str, str]:
    return {"kind": kind, "id": "LEGITEXT000000000001", "label": label}


def test_le_document_porte_les_champs_du_contrat_et_ses_passages() -> None:
    body = build_index_document(
        _doc(metadata={"num": "3"}), SearchContent(passages=(_passage([0.5, 0.5]),))
    )

    assert body["identifier"] == IDENTIFIER.serialize()
    assert body["document_type"] == "article"
    assert body["nature"] is None
    assert body["title"] == "3"
    assert body["metadata"] == {"num": "3"}
    assert body["passages"] == [
        {
            "chunk_id": "LEGIARTI000045938851_0000",
            "char_start": 0,
            "char_end": 18,
            "text": "Le passage indexé.",
            "embedding": [0.5, 0.5],
        }
    ]


def test_un_passage_sans_vecteur_na_PAS_de_champ_embedding() -> None:
    """ADR-012 : l'embedding coupé, le passage reste cherchable par son texte."""
    body = build_index_document(_doc(), SearchContent(passages=(_passage(None),)))

    assert "embedding" not in body["passages"][0]


def test_le_vecteur_de_titre_nest_pose_QUE_sil_existe() -> None:
    without = build_index_document(_doc(), SearchContent())
    with_title = build_index_document(_doc(), SearchContent(title_embedding=[1.0]))

    assert "title_embedding" not in without
    assert with_title["title_embedding"] == [1.0]


def test_parent_text_title_garde_les_TITRE_TXT_sans_doublon_dans_lordre() -> None:
    """Un titre par période, souvent le même ; les ``TITRE_TM`` titrent des
    subdivisions, pas le texte."""
    context = [
        _title("TITRE_TXT", DECREE),
        _title("TITRE_TM", "Chapitre Ier"),
        _title("TITRE_TXT", DECREE_VARIANT),
        _title("TITRE_TXT", DECREE),
    ]

    body = build_index_document(_doc(context=context), SearchContent())

    assert body["parent_text_title"] == [DECREE, DECREE_VARIANT]


def test_sans_texte_parent_le_champ_est_ABSENT() -> None:
    body = build_index_document(_doc(), SearchContent())

    assert "parent_text_title" not in body


def test_une_metadonnee_homonyme_reste_sous_metadata() -> None:
    """Une métadonnée ``identifier`` ne peut pas écraser le champ du contrat."""
    body = build_index_document(_doc(metadata={"identifier": "faux"}), SearchContent())

    assert body["identifier"] == IDENTIFIER.serialize()
    assert body["metadata"] == {"identifier": "faux"}


def test_les_deux_champs_vectoriels_ont_la_MEME_dimension() -> None:
    """``check_vector_dimension`` ne lit que celle des passages."""
    properties = _load_index_definition()["mappings"]["properties"]

    passages = properties["passages"]["properties"]["embedding"]["dimension"]
    assert properties["title_embedding"]["dimension"] == passages


def test_un_modele_dune_autre_dimension_est_REFUSE() -> None:
    check_vector_dimension(768)

    with pytest.raises(ValueError, match="dimension 1024"):
        check_vector_dimension(1024)
