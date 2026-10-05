"""Le chunker : des offsets exacts, et aucun chunk vide."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.processing import ChunkingConfig
from ragcore.core.ports.chunker import BaseChunker
from ragcore.sources.generic import GenericParser, StructuralChunker, to_tree
from ragcore.sources.generic.chunking import _windows
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE

# Du vrai XML : un arbre inventé n'aurait ni <p> imbriqués ni facettes fusionnées
from ragcore.sources.legislatif.tests.conftest import (
    ARTICLE_RICHE,
    ARTICLE_SIMPLE,
    SECTION_ARTICLES,
)

# Plus petits que la configuration réelle : les fixtures doivent être découpées
CHUNK_SIZE = 128
OVERLAP = 25


def _parse(fixtures_dir: Path, name: str) -> ParsedDocument:
    return _parse_result(fixtures_dir, name).document


def _parse_result(fixtures_dir: Path, name: str):
    return GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI).parse(
        RawDocument(
            source=SourceName.LEGI,
            source_document_id=name,
            payload={
                "content": [to_tree(ET.parse(fixtures_dir / name).getroot())],
                "files": [name],
            },
            fetched_at=datetime.now(UTC),
        )
    )


def _chunker() -> StructuralChunker:
    return StructuralChunker(
        ChunkingConfig(max_chars=CHUNK_SIZE, overlap_chars=OVERLAP)
    )


def test_le_chunker_satisfait_son_port() -> None:
    assert isinstance(_chunker(), BaseChunker)


def test_aucun_chunk_ne_depasse_la_taille_maximale(fixtures_dir: Path) -> None:
    """La structure borne le découpage sans le remplacer : un long article est découpé
    à la taille, même dans un seul bloc."""
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    chunks = _chunker().chunk(document)

    assert len(document.content) > CHUNK_SIZE * 10  # le cas est bien réel
    assert chunks
    for chunk in chunks:
        assert len(chunk.text) <= CHUNK_SIZE


def test_les_offsets_designent_le_vrai_texte(fixtures_dir: Path) -> None:
    """``content[char_start:char_end]`` rend exactement ``chunk.text`` : un offset faux
    citerait le mauvais passage sans rien lever."""
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")

    for chunk in _chunker().chunk(document):
        assert document.content[chunk.char_start : chunk.char_end] == chunk.text


def test_le_decoupage_couvre_tout_le_contenu(fixtures_dir: Path) -> None:
    """Rien ne se perd : le dernier offset atteint la fin du contenu."""
    document = _parse(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    chunks = _chunker().chunk(document)

    assert chunks[0].char_start == 0
    assert chunks[-1].char_end == len(document.content)


def test_un_document_sans_contenu_ne_rend_AUCUN_chunk(fixtures_dir: Path) -> None:
    """Une section sans texte ne donne aucun chunk : un vecteur de néant pourrait être
    proposé comme source."""
    document = _parse(fixtures_dir, f"{SECTION_ARTICLES}.xml")

    assert document.content == ""
    assert _chunker().chunk(document) == []


def test_les_chunks_sont_numerotes_sans_trou_ni_doublon(fixtures_dir: Path) -> None:
    """Des ordinaux distincts : le backend dédoublonne les passages par ``chunk_id``,
    et confondrait deux passages de même identifiant."""
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    chunks = _chunker().chunk(document)

    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_le_chunk_id_derive_de_lidentifiant_du_parent(fixtures_dir: Path) -> None:
    """Deux workers sur des documents distincts ne touchent jamais le même chunk."""
    document = _parse(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")

    for chunk in _chunker().chunk(document):
        assert chunk.chunk_id.startswith(ARTICLE_SIMPLE)
        assert chunk.parent_identifier == document.identifier


def test_le_chemin_structurel_est_porte_par_le_chunk(fixtures_dir: Path) -> None:
    """La découpe structurelle tourne, et le chemin est renseigné."""
    document = _parse(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    chunks = _chunker().chunk(document)

    assert all(chunk.tag_path == ["ARTICLE", "BLOC_TEXTUEL"] for chunk in chunks)


def test_sans_section_declaree_le_document_entier_est_un_bloc() -> None:
    """Sans structure, le document entier est un bloc découpé à la taille."""
    document = _document(content="a" * 300, sections=[])
    chunks = _chunker().chunk(document)

    assert len(chunks) > 1
    assert all(chunk.tag_path == [] for chunk in chunks)
    assert chunks[-1].char_end == 300


def test_aucune_fenetre_n_est_contenue_dans_une_autre() -> None:
    """Un fort chevauchement ne produit pas de fenêtres de queue incluses dans la
    précédente."""
    fenetres = _windows(length=10, size=8, overlap=6)

    assert fenetres == [(0, 8), (2, 10)]
    # Aucune fenêtre n'est un sous-intervalle d'une autre.
    for i, (a0, a1) in enumerate(fenetres):
        for j, (b0, b1) in enumerate(fenetres):
            if i != j:
                assert not (b0 <= a0 and a1 <= b1), f"{fenetres[i]} ⊂ {fenetres[j]}"


def test_les_fenetres_couvrent_toujours_tout() -> None:
    """L'arrêt anticipé ne laisse rien de côté : la dernière fenêtre atteint la fin."""
    for length, size, overlap in [(10, 8, 6), (100, 10, 3), (7, 8, 2), (50, 20, 19)]:
        fenetres = _windows(length=length, size=size, overlap=overlap)
        assert fenetres[0][0] == 0
        assert fenetres[-1][1] == length


def _document(content: str, sections: list[dict[str, Any]]) -> ParsedDocument:
    return ParsedDocument(
        identifier=Identifier(raw="LEGIARTI000000000001"),
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title="t",
        content=content,
        structure={"sections": sections, "references": [], "context": []},
        metadata={},
        parsed_at=datetime.now(UTC),
    )
