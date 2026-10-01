"""Les collisions de métadonnées (ADR-049) : dédoublonner, lister, ou refuser.

Une table minuscule, deux racines déclarées dans l'ordre ``VERSION`` puis ``STRUCT`` :
assez pour éprouver l'ordre des facettes sans dépendre du vocabulaire de LEGI.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import pytest

from ragcore.core.exceptions import CollisionError, ValidationError
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.ports.parser import ParseResult
from ragcore.sources.generic import GenericParser, Role, RoleTable, to_tree

_ID = "LEGITEXT000000000001"

_TABLE = RoleTable(
    roots=("VERSION", "STRUCT"),
    roles={
        **dict.fromkeys(("VERSION", "STRUCT", "META", "ID"), Role.META),
        **dict.fromkeys(("URL", "NUM", "MOT", "DATE"), Role.META),
    },
    document_types={"LEGITEXT": DocumentType.TEXTE},
    meta_containers=("META",),
    meta_renames={"URL": "url", "NUM": "num", "DATE": "date"},
    list_keys=frozenset({"url", "date"}),
)


def _facet(root: str, meta: str) -> str:
    return f"<{root}><META><ID>{_ID}</ID>{meta}</META></{root}>"


def _parse(*facets: str) -> ParseResult:
    raw = RawDocument(
        source=SourceName.LEGI,
        source_document_id=_ID,
        payload={
            "content": [to_tree(ET.fromstring(facet)) for facet in facets],
            "files": [f"{index}.xml" for index in range(len(facets))],
        },
        fetched_at=datetime.now(UTC),
    )
    return GenericParser(_TABLE, SourceName.LEGI).parse(raw)


def test_des_valeurs_identiques_ne_font_pas_de_collision() -> None:
    result = _parse(
        _facet("STRUCT", "<NUM>42</NUM>"), _facet("VERSION", "<NUM>42</NUM>")
    )

    assert result.document.metadata["num"] == "42"
    assert result.collisions == ()


def test_une_cle_list_est_toujours_une_liste() -> None:
    result = _parse(_facet("VERSION", "<URL>v.xml</URL>"))

    assert result.document.metadata["url"] == ["v.xml"]


def test_les_valeurs_suivent_l_ordre_DECLARE_des_facettes() -> None:
    """``STRUCT`` arrive en premier, mais la table déclare ``VERSION`` d'abord."""
    result = _parse(
        _facet("STRUCT", "<URL>s.xml</URL>"), _facet("VERSION", "<URL>v.xml</URL>")
    )

    assert result.document.metadata["url"] == ["v.xml", "s.xml"]
    (collision,) = result.collisions
    assert collision.key == "url"
    assert [value.root for value in collision.values] == ["VERSION", "STRUCT"]
    assert [value.source_file for value in collision.values] == ["1.xml", "0.xml"]
    assert collision.source_files() == ("1.xml", "0.xml")
    assert collision.values[0].path == "VERSION/META/URL"


def test_une_collision_garde_toutes_les_occurrences_doublons_compris() -> None:
    result = _parse(
        _facet("VERSION", "<DATE>2020</DATE><DATE>2021</DATE>"),
        _facet("STRUCT", "<DATE>2020</DATE>"),
    )

    assert result.document.metadata["date"] == ["2020", "2021"]
    (collision,) = result.collisions
    assert [value.value for value in collision.values] == ["2020", "2021", "2020"]
    assert collision.source_files() == ("0.xml", "1.xml")


def test_une_cle_renommee_hors_list_en_collision_REFUSE_le_document() -> None:
    with pytest.raises(CollisionError) as refused:
        _parse(_facet("VERSION", "<NUM>1</NUM><NUM>2</NUM>"))

    (collision,) = refused.value.collisions
    assert collision.key == "num"
    assert collision.identifier == _ID
    assert collision.source is SourceName.LEGI
    assert collision.source_files() == ("0.xml",)


def test_une_cle_NON_renommee_en_collision_devient_une_liste() -> None:
    result = _parse(_facet("VERSION", "<MOT>a</MOT><MOT>b</MOT>"))

    assert result.document.metadata["version_meta_mot"] == ["a", "b"]
    assert [collision.key for collision in result.collisions] == ["version_meta_mot"]


def test_une_racine_non_declaree_rend_l_ordre_indetermine() -> None:
    with pytest.raises(ValidationError, match="Ordre des facettes"):
        _parse(_facet("VERSION", ""), _facet("AUTRE", ""))


def test_deux_facettes_de_meme_racine_rendent_l_ordre_indetermine() -> None:
    with pytest.raises(ValidationError, match="Ordre des facettes"):
        _parse(_facet("VERSION", ""), _facet("VERSION", ""))


def test_une_facette_seule_de_racine_inconnue_reste_un_signal() -> None:
    """Une seule facette n'a pas d'ordre à décider : la racine inconnue est signalée,
    comme avant (ADR-048)."""
    result = _parse(_facet("AUTRE", ""))

    assert result.unknown_roots == {"AUTRE": "0.xml"}
