"""Le parser sur LEGI : ce qu'il interprète, et ce qu'il refuse d'inventer."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest

from ragcore.core.exceptions import ParseError, ValidationError
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.enums import SourceName as _SN
from ragcore.core.ports.parser import BaseParser
from ragcore.sources.generic import GenericParser, to_tree
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE

from .conftest import (
    ARTICLE_INCONNU,
    ARTICLE_SIMPLE,
    SECTION_ARTICLES,
    SECTION_MIXTE,
    TEXTE_DEUX_FACETTES,
)


def _raw(fixtures_dir: Path, *names: str) -> RawDocument:
    return RawDocument(
        source=SourceName.LEGI,
        source_document_id=names[0],
        payload={
            "content": [
                to_tree(ET.parse(fixtures_dir / name).getroot()) for name in names
            ],
            "files": list(names),
        },
        fetched_at=datetime.now(UTC),
    )


def test_le_parser_satisfait_son_port() -> None:
    assert isinstance(GenericParser(LEGI_ROLE_TABLE, _SN.LEGI), BaseParser)


def test_le_contenu_reste_du_FRANCAIS(fixtures_dir: Path) -> None:
    """Le contenu n'est pas lemmatisé : les mots vides (« le », « est », « par »)
    prouvent que le texte est intact."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(_raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml"))
        .document
    )

    assert "Le directeur général est nommé par décret" in parsed.content
    assert "pour une durée de trois ans renouvelable" in parsed.content


def test_lidentifiant_vient_du_ID_car_il_nexiste_aucune_balise_ELI(
    fixtures_dir: Path,
) -> None:
    """Le corpus n'a aucune balise ``<ELI>`` : l'identifiant est un ``<ID>``."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(_raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml"))
        .document
    )

    assert parsed.identifier.raw == ARTICLE_SIMPLE
    assert parsed.identifier.serialize() == ARTICLE_SIMPLE


def test_les_deux_facettes_du_texte_donnent_UN_document_avec_son_titre(
    fixtures_dir: Path,
) -> None:
    """``TEXTELR`` n'a pas de titre, ``TEXTE_VERSION`` pas de structure : lues
    ensemble, elles donnent le document."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(
            _raw(
                fixtures_dir,
                f"{TEXTE_DEUX_FACETTES}-version.xml",
                f"{TEXTE_DEUX_FACETTES}-struct.xml",
            )
        )
        .document
    )

    assert parsed.identifier.raw == TEXTE_DEUX_FACETTES
    assert parsed.title.startswith("Décret n°2016-1967")  # vient de TEXTE_VERSION
    assert not any(key.endswith("_titre") for key in parsed.metadata), (
        "le titre a son champ dédié : le recopier en métadonnée ferait deux vérités"
    )
    assert parsed.metadata["num"] == "2016-1967"  # renommé : reste une métadonnée
    assert _kinds(parsed.structure["references"]) & {
        "LIEN_SECTION_TA"
    }  # vient de TEXTELR


def test_URL_nest_ni_une_metadonnee_ni_un_signal(fixtures_dir: Path) -> None:
    """ADR-027 : ``URL`` a le rôle ``IGNORED``. Chaque facette d'un texte porte la
    sienne : sans ce rôle, elle reviendrait en métadonnée et en collision."""
    result = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(
            fixtures_dir,
            f"{TEXTE_DEUX_FACETTES}-version.xml",
            f"{TEXTE_DEUX_FACETTES}-struct.xml",
        )
    )

    assert not any(key.endswith("url") for key in result.document.metadata)
    assert not any(key.endswith("url") for key in result.unconfigured_tags)
    assert result.collisions == ()


def test_le_texte_dun_decret_nest_PAS_dans_un_BLOC_TEXTUEL(fixtures_dir: Path) -> None:
    """Aucun ``TEXTE_VERSION`` n'a de ``<BLOC_TEXTUEL>`` : son texte vit sous
    ``<VISAS>``, ``<SIGNATAIRES>`` et ``<TP>``."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(
            _raw(
                fixtures_dir,
                f"{TEXTE_DEUX_FACETTES}-version.xml",
                f"{TEXTE_DEUX_FACETTES}-struct.xml",
            )
        )
        .document
    )

    assert "Le Premier ministre" in parsed.content
    assert "Vu le code" in parsed.content


def test_chaque_section_est_un_morceau_LITTERAL_du_contenu(fixtures_dir: Path) -> None:
    """``_content`` et ``_sections`` lisent les mêmes blocs, dans le même ordre : sinon
    les offsets des chunks pointeraient à côté."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(_raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml"))
        .document
    )

    assert parsed.structure["sections"]
    for section in parsed.structure["sections"]:
        assert section["text"] in parsed.content


def test_une_section_na_pas_de_contenu_et_ce_nest_pas_un_echec(
    fixtures_dir: Path,
) -> None:
    """Une ``SECTION_TA`` est un nœud de structure : contenu vide, donc aucun chunk."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(_raw(fixtures_dir, f"{SECTION_ARTICLES}.xml"))
        .document
    )

    assert parsed.content == ""
    assert parsed.structure["sections"] == []
    assert parsed.title.startswith("Section 3")
    assert len(parsed.structure["references"]) == 14  # ses articles, eux, sont là


def test_le_parser_rend_les_liens_BRUTS_sans_les_typer(fixtures_dir: Path) -> None:
    """Le parser rend le vocabulaire de LEGI tel quel : seul ``core/links`` traduit."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(_raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml"))
        .document
    )

    (lien,) = [r for r in parsed.structure["references"] if r["kind"] == "LIEN"]
    assert lien["typelien"] == "CREE"  # le mot de LEGI, pas encore traduit
    assert lien["sens"] == "cible"


def test_le_contexte_porte_la_fermeture_des_ancetres(fixtures_dir: Path) -> None:
    """``<CONTEXTE>`` déclare tous les ancêtres d'un coup, d'où la réduction en aval."""
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(_raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml"))
        .document
    )

    context = parsed.structure["context"]
    assert len(context) > 1, "un seul ancêtre ne serait pas une fermeture"
    assert any(c["id"].startswith("LEGITEXT") for c in context)  # le texte parent
    assert any(c["id"].startswith("LEGISCTA") for c in context)  # ses sections


def test_une_balise_non_configuree_est_ROUTEE_et_SIGNALEE(fixtures_dir: Path) -> None:
    """Le corpus réel n'a aucune balise absente de la table : la fixture synthétique
    vérifie que ``<ZORG>`` est à la fois signalée et ingérée sous sa clé chemin-complet.
    """
    result = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, "unknown_vocabulary.xml")
    )
    parsed = result.document

    # Le texte et l'attribut, sous des clés chemin-complet
    assert parsed.metadata["article_zorg"] == "Une balise que le parser ne connaît pas."
    assert parsed.metadata["article_zorg_attribut_inconnu"] == "peu importe"
    # Le signal, par clé, avec le fichier où le lire
    assert result.unconfigured_tags == {
        "article_zorg": "unknown_vocabulary.xml",
        "article_zorg_attribut_inconnu": "unknown_vocabulary.xml",
    }
    assert parsed.identifier.raw == ARTICLE_INCONNU
    assert "texte parfaitement ordinaire" in parsed.content  # le reste est parsé


def test_une_balise_connue_SANS_RENOMMAGE_est_non_configuree() -> None:
    """ADR-023 : ``MINISTERE``, rôle ``META`` sans renommage, entre sous sa clé
    chemin-complet et est signalée. ``ORIGINE``, renommée, ne l'est pas."""
    tree = to_tree(
        ET.fromstring(
            "<ARTICLE><META>"
            f"<META_COMMUN><ID>{ARTICLE_INCONNU}</ID><ORIGINE>LEGI</ORIGINE></META_COMMUN>"
            "<META_SPEC><META_ARTICLE>"
            "<MINISTERE>Justice</MINISTERE>"
            "</META_ARTICLE></META_SPEC>"
            "</META></ARTICLE>"
        )
    )
    result = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        RawDocument(
            source=SourceName.LEGI,
            source_document_id="x",
            payload={"content": [tree]},
            fetched_at=datetime.now(UTC),
        )
    )
    key = "article_meta_meta_spec_meta_article_ministere"

    assert result.unconfigured_tags == {key: ""}  # aucun fichier
    assert result.document.metadata[key] == "Justice"
    assert result.document.metadata["origine"] == "LEGI"


def test_une_valeur_au_format_DILA_devient_un_LIEN_pas_une_metadonnee(
    fixtures_dir: Path,
) -> None:
    """Une valeur non configurée au format DILA pointe : elle devient un lien. Sauf
    l'identifiant du document lui-même, qui reste une métadonnée."""
    tree = to_tree(
        ET.fromstring(
            "<ARTICLE>"
            f"<META><META_COMMUN><ID>{ARTICLE_INCONNU}</ID></META_COMMUN></META>"
            "<ZORG_REF>LEGIARTI000000424242</ZORG_REF>"
            f"<ZORG_SELF>{ARTICLE_INCONNU}</ZORG_SELF>"
            "</ARTICLE>"
        )
    )
    result = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        RawDocument(
            source=SourceName.LEGI,
            source_document_id="x",
            payload={"content": [tree]},
            fetched_at=datetime.now(UTC),
        )
    )
    parsed = result.document

    # ZORG_REF pointe ailleurs : un lien heuristique
    heuristic = [r for r in parsed.structure["references"] if r["tag"] == "ZORG_REF"]
    assert [r["id"] for r in heuristic] == ["LEGIARTI000000424242"]
    assert "article_zorg_ref" not in parsed.metadata
    # ZORG_SELF porte l'identité du document : une métadonnée
    assert parsed.metadata["article_zorg_self"] == ARTICLE_INCONNU
    # Les deux sont signalées, chacune sous sa porte
    assert result.unconfigured_links == {"article_zorg_ref": ""}
    assert result.unconfigured_tags == {"article_zorg_self": ""}


def test_une_balise_non_configuree_VIDE_ne_laisse_aucune_trace() -> None:
    """Sans texte ni attribut, ni métadonnée ni signal : le signal naît des valeurs
    (ADR-024)."""
    tree = to_tree(
        ET.fromstring(
            "<ARTICLE>"
            f"<META><META_COMMUN><ID>{ARTICLE_INCONNU}</ID></META_COMMUN></META>"
            "<ZORG_VIDE/>"
            "</ARTICLE>"
        )
    )
    result = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        RawDocument(
            source=SourceName.LEGI,
            source_document_id="x",
            payload={"content": [tree]},
            fetched_at=datetime.now(UTC),
        )
    )

    assert result.unconfigured_tags == {}
    assert result.unconfigured_links == {}
    assert "article_zorg_vide" not in result.document.metadata


def test_un_xml_illisible_leve_ParseError_pas_ValidationError(
    fixtures_dir: Path,
) -> None:
    """Une panne de lecture n'est pas un refus métier : les confondre empêcherait de
    savoir quoi réparer."""
    with pytest.raises(ET.ParseError):
        ET.parse(fixtures_dir / "malformed.xml")

    with pytest.raises(ParseError):
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id="x",
                payload={"content": []},  # le connecteur n'a rien pu transcrire
                fetched_at=datetime.now(UTC),
            )
        )


def test_un_document_sans_identifiant_leve_ValidationError() -> None:
    """Lisible, mais irrecevable : c'est un rejet métier."""
    tree = to_tree(ET.fromstring("<ARTICLE><META/></ARTICLE>"))

    with pytest.raises(ValidationError, match="Identifiant absent"):
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id="x",
                payload={"content": [tree]},
                fetched_at=datetime.now(UTC),
            )
        )


def test_un_identifiant_mal_forme_leve_ValidationError() -> None:
    """Sans relais, l'erreur pydantic serait comptée en panne de lecture."""
    tree = to_tree(ET.fromstring("<ARTICLE><ID>PAS_UN_ELI</ID></ARTICLE>"))

    with pytest.raises(ValidationError, match="Identifiant invalide"):
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id="x",
                payload={"content": [tree]},
                fetched_at=datetime.now(UTC),
            )
        )


@pytest.mark.parametrize(
    ("files", "document_type", "nature"),
    [
        # « Article » : son type le dit déjà
        ((f"{ARTICLE_SIMPLE}.xml",), DocumentType.ARTICLE, None),
        ((f"{SECTION_MIXTE}.xml",), DocumentType.SECTION, None),
        (
            (
                f"{TEXTE_DEUX_FACETTES}-version.xml",
                f"{TEXTE_DEUX_FACETTES}-struct.xml",
            ),
            DocumentType.TEXTE,
            "DECRET",
        ),
    ],
)
def test_le_type_vient_du_prefixe_et_la_nature_de_NATURE(
    fixtures_dir: Path,
    files: tuple[str, ...],
    document_type: DocumentType,
    nature: str | None,
) -> None:
    parsed = (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(_raw(fixtures_dir, *files))
        .document
    )

    assert parsed.document_type == document_type
    assert parsed.nature == nature
    assert not {"nature", "type_document"} & parsed.metadata.keys(), (
        "la nature a son champ dédié : la recopier en métadonnée ferait deux vérités"
    )


def test_un_prefixe_sans_type_declare_leve_ValidationError() -> None:
    """Aucun document n'entre sans type : un préfixe que la table ignore est refusé."""
    tree = to_tree(ET.fromstring("<ARTICLE><ID>JORFARTI000000000001</ID></ARTICLE>"))

    with pytest.raises(ValidationError, match="sans type de document"):
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id="x",
                payload={"content": [tree]},
                fetched_at=datetime.now(UTC),
            )
        )


def _kinds(references: list[dict[str, Any]]) -> set[str]:
    return {reference["kind"] for reference in references}
