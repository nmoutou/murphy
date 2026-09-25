"""Le chunker : des offsets qui ne mentent pas, et aucun chunk de néant."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest

from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import ELI, OwnerId
from ragcore.core.ports.chunker import BaseChunker
from ragcore.sources.generic import GenericParser, StructuralChunker, to_tree
from ragcore.sources.generic.chunking import _windows
from ragcore.sources.legi.table import LEGI_ROLE_TABLE

# Le chunker est GÉNÉRIQUE, mais il faut du VRAI XML pour l'éprouver — un arbre inventé ne
# porterait ni les <p> imbriqués, ni les facettes fusionnées. `fixtures_dir` arrive par la
# conftest locale ; ici on n'importe que les identifiants des fixtures.
from ragcore.sources.legi.tests.conftest import (
    ARTICLE_RICHE,
    ARTICLE_SIMPLE,
    SECTION_ARTICLES,
)

OWNER = OwnerId("u1")

# Les vrais paramètres du pipeline (conf/base/parameters.yml).
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
            owner_id=OWNER,
        )
    )


def _chunker() -> StructuralChunker:
    return StructuralChunker(max_chunk_size=CHUNK_SIZE, overlap=OVERLAP)


def test_le_chunker_satisfait_son_port() -> None:
    assert isinstance(_chunker(), BaseChunker)


def test_aucun_chunk_ne_depasse_la_taille_maximale(fixtures_dir: Path) -> None:
    """LE test du chunker.

    L'ancienne version choisissait entre découpe structurelle *ou* taille fixe. Dès
    qu'un bloc existait, elle le rendait ENTIER : un article de 2914 caractères donnait
    un chunk de 2914 caractères, quand ``chunk_size`` en vaut 128.

    L'embedder l'aurait tronqué en silence — la fenêtre d'``all-mpnet-base-v2`` est de
    384 tokens — et les trois quarts du texte se seraient évaporés sans qu'aucune
    exception ne soit levée. La structure borne le découpage ; elle ne le remplace pas.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    chunks = _chunker().chunk(document)

    assert len(document.content) > CHUNK_SIZE * 10  # le cas est bien réel
    assert chunks
    for chunk in chunks:
        assert len(chunk.text) <= CHUNK_SIZE


def test_les_offsets_designent_le_vrai_texte(fixtures_dir: Path) -> None:
    """``content[char_start:char_end]`` DOIT rendre exactement ``chunk.text``.

    L'ancienne version faisait ``content.find(text)`` et posait ``char_start = 0`` quand
    elle ne trouvait pas. Un offset faux ne lève rien : il désigne le mauvais passage, et
    personne ne s'en aperçoit — jusqu'à ce qu'un utilisateur reçoive une citation qui
    n'est pas celle du document.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")

    for chunk in _chunker().chunk(document):
        assert document.content[chunk.char_start : chunk.char_end] == chunk.text


def test_le_decoupage_couvre_tout_le_contenu(fixtures_dir: Path) -> None:
    """Rien ne se perd entre le contenu et ses chunks : le dernier offset atteint la fin.
    Une fenêtre manquante, c'est un passage du texte qui ne sera jamais retrouvable.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    chunks = _chunker().chunk(document)

    assert chunks[0].char_start == 0
    assert chunks[-1].char_end == len(document.content)


def test_un_document_sans_contenu_ne_rend_AUCUN_chunk(fixtures_dir: Path) -> None:
    """Mesuré : 0/287 ``SECTION_TA`` ont du texte. Une section est un nœud de structure,
    pas un porteur de contenu.

    Lui fabriquer un chunk vide reviendrait à embarquer du néant — un vecteur sans
    signification, que la recherche sémantique pourrait remonter et proposer à un
    utilisateur comme une source.
    """
    document = _parse(fixtures_dir, f"{SECTION_ARTICLES}.xml")

    assert document.content == ""
    assert _chunker().chunk(document) == []


def test_les_chunks_sont_numerotes_sans_trou_ni_doublon(fixtures_dir: Path) -> None:
    """Le ``chunk_id`` dérive de l'ordinal : deux chunks au même ordinal auraient le même
    identifiant, et l'un écraserait l'autre dans Qdrant. Silencieusement.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    chunks = _chunker().chunk(document)

    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_le_chunk_id_derive_de_lidentifiant_du_parent(fixtures_dir: Path) -> None:
    """C'est ce qui garantit (§11) que deux sagas sur des documents distincts ne peuvent
    pas se marcher dessus sur un même chunk : la sûreté vient de la PARTITION, pas d'un
    verrou.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")

    for chunk in _chunker().chunk(document):
        assert chunk.chunk_id.startswith(ARTICLE_SIMPLE)
        assert chunk.parent_identifier == document.identifier


def test_le_chemin_structurel_est_porte_par_le_chunk(fixtures_dir: Path) -> None:
    """La structure n'a jamais tourné : ``structure["sections"]`` était lu par le chunker
    et écrit par personne. Le repli à taille fixe s'appliquait TOUJOURS, et le chemin
    était toujours vide.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    chunks = _chunker().chunk(document)

    assert all(chunk.tag_path == ["ARTICLE", "BLOC_TEXTUEL"] for chunk in chunks)


def test_sans_section_declaree_le_document_entier_est_un_bloc() -> None:
    """La découpe à taille fixe n'est pas un mode à part : c'est le cas particulier où la
    structure est muette.
    """
    document = _document(content="a" * 300, sections=[])
    chunks = _chunker().chunk(document)

    assert len(chunks) > 1
    assert all(chunk.tag_path == [] for chunk in chunks)
    assert chunks[-1].char_end == 300


def test_un_chevauchement_plus_grand_que_la_taille_est_refuse() -> None:
    """Le curseur n'avancerait pas : boucle infinie. Mieux vaut le dire à la construction
    que de faire tourner un run qui ne se termine jamais.
    """
    with pytest.raises(ValueError, match="strictement inférieur"):
        StructuralChunker(max_chunk_size=100, overlap=100)


def test_aucune_fenetre_n_est_contenue_dans_une_autre() -> None:
    """F18 : un fort chevauchement produisait des fenêtres de queue redondantes.

    ``length=10, size=8, overlap=6`` (step=2) donnait ``(0,8),(2,10),(4,10),(6,10),
    (8,10)`` : les trois dernières sont incluses dans ``(2,10)``. Autant de chunks
    dupliqués dans l'index, du même texte compté plusieurs fois à la recherche. On
    s'arrête dès qu'une fenêtre atteint la fin.
    """
    fenetres = _windows(length=10, size=8, overlap=6)

    assert fenetres == [(0, 8), (2, 10)]
    # Aucune fenêtre n'est un sous-intervalle d'une autre.
    for i, (a0, a1) in enumerate(fenetres):
        for j, (b0, b1) in enumerate(fenetres):
            if i != j:
                assert not (b0 <= a0 and a1 <= b1), f"{fenetres[i]} ⊂ {fenetres[j]}"


def test_les_fenetres_couvrent_toujours_tout() -> None:
    """L'arrêt anticipé ne doit rien laisser de côté : la dernière fenêtre atteint la fin."""
    for length, size, overlap in [(10, 8, 6), (100, 10, 3), (7, 8, 2), (50, 20, 19)]:
        fenetres = _windows(length=length, size=size, overlap=overlap)
        assert fenetres[0][0] == 0
        assert fenetres[-1][1] == length


def _document(content: str, sections: list[dict[str, Any]]) -> ParsedDocument:
    return ParsedDocument(
        identifier=ELI(raw="LEGIARTI000000000001"),
        source=SourceName.LEGI,
        owner_id=OWNER,
        title="t",
        content=content,
        structure={"sections": sections, "references": [], "context": []},
        metadata={},
        parsed_at=datetime.now(UTC),
    )
