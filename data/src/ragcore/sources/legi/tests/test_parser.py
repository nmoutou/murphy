"""Le parser : ce qu'il interprète, et ce qu'il refuse d'inventer."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest

from ragcore.core.exceptions import ParseError, ValidationError
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.enums import SourceName as _SN
from ragcore.core.models.identifiers import OwnerId
from ragcore.core.ports.parser import BaseParser
from ragcore.core.services.unknown_categories import CATEGORY_TAG
from ragcore.sources.generic import GenericParser
from ragcore.sources.legi.file_connector import _to_tree
from ragcore.sources.legi.table import LEGI_ROLE_TABLE

from .conftest import (
    ARTICLE_INCONNU,
    ARTICLE_SIMPLE,
    SECTION_ARTICLES,
    TEXTE_DEUX_FACETTES,
)

OWNER = OwnerId("u1")


def _raw(fixtures_dir: Path, *names: str) -> RawDocument:
    """Fabrique le RawDocument que le connecteur produirait pour ces fichiers."""
    return RawDocument(
        source=SourceName.LEGI,
        source_document_id=names[0],
        payload={
            "content": [
                _to_tree(ET.parse(fixtures_dir / name).getroot()) for name in names
            ],
            "files": list(names),
        },
        fetched_at=datetime.now(UTC),
        owner_id=OWNER,
    )


def test_le_parser_satisfait_son_port() -> None:
    assert isinstance(GenericParser(LEGI_ROLE_TABLE, _SN.LEGI), BaseParser)


def test_le_contenu_reste_du_FRANCAIS(fixtures_dir: Path) -> None:
    """LE test du parser. L'ancien ``_clean_text`` lemmatisait le contenu :

        « Le directeur général est nommé par décret »  ->  « directeur général nommer décret »

    Ce sac de lemmes partait dans Mongo — donc s'affichait à l'utilisateur comme
    *source* — et était embarqué par un modèle de phrases entraîné sur du texte
    naturel. L'original n'était stocké nulle part.

    Les mots vides (« le », « est », « par », « une ») sont la preuve que le texte est
    intact : ce sont exactement eux que la lemmatisation supprimait.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    )

    assert "Le directeur général est nommé par décret" in parsed.content
    assert "pour une durée de trois ans renouvelable" in parsed.content


def test_lidentifiant_vient_du_ID_car_il_nexiste_aucune_balise_ELI(
    fixtures_dir: Path,
) -> None:
    """Vérifié sur les 2564 fichiers : ``<ELI>`` n'existe nulle part. Le nom du modèle
    est historique ; la donnée est un ``<ID>``.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    )

    assert parsed.identifier.raw == ARTICLE_SIMPLE
    assert parsed.identifier.serialize() == f"eli:{ARTICLE_SIMPLE}"


def test_les_deux_facettes_du_texte_donnent_UN_document_avec_son_titre(
    fixtures_dir: Path,
) -> None:
    """La conséquence de la fusion, côté parser.

    ``TEXTELR`` n'a AUCUN titre (0/98 mesuré) et ``TEXTE_VERSION`` aucune structure.
    Lues séparément, l'une donnerait un document sans titre et l'autre un document sans
    sections. Lues ensemble, elles donnent le document.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(
            fixtures_dir,
            f"{TEXTE_DEUX_FACETTES}-version.xml",
            f"{TEXTE_DEUX_FACETTES}-struct.xml",
        )
    )

    assert parsed.identifier.raw == TEXTE_DEUX_FACETTES
    assert parsed.title.startswith("Décret n°2016-1967")  # vient de TEXTE_VERSION
    assert _kinds(parsed.structure["references"]) & {
        "LIEN_SECTION_TA"
    }  # vient de TEXTELR


def test_le_texte_dun_decret_nest_PAS_dans_un_BLOC_TEXTUEL(fixtures_dir: Path) -> None:
    """Mesuré : **aucun** ``TEXTE_VERSION`` n'a de ``<BLOC_TEXTUEL>`` (0/98). Son texte
    vit sous ``<VISAS>`` (« Vu le code général… »), ``<SIGNATAIRES>`` et ``<TP>``.

    Ne chercher que ``BLOC_TEXTUEL`` aurait ingéré les 98 décrets du corpus avec un
    contenu VIDE — sans qu'une seule exception soit levée.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(
            fixtures_dir,
            f"{TEXTE_DEUX_FACETTES}-version.xml",
            f"{TEXTE_DEUX_FACETTES}-struct.xml",
        )
    )

    assert "Le Premier ministre" in parsed.content
    assert "Vu le code" in parsed.content


def test_chaque_section_est_un_morceau_LITTERAL_du_contenu(fixtures_dir: Path) -> None:
    """``_content`` et ``_sections`` lisent les MÊMES blocs, dans le même ordre.

    Les faire diverger, c'est garantir que le chunker calculera des ``char_start`` qui
    ne pointent nulle part dans ``content`` — des offsets qui mentent, et que rien ne
    signale.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    )

    assert parsed.structure["sections"]
    for section in parsed.structure["sections"]:
        assert section["text"] in parsed.content


def test_une_section_na_pas_de_contenu_et_ce_nest_pas_un_echec(
    fixtures_dir: Path,
) -> None:
    """Mesuré : 0/287 ``SECTION_TA`` ont un bloc textuel. Une section est un nœud de
    structure, pas un porteur de texte. Rendre la chaîne vide est la VÉRITÉ — et le
    chunker n'en fera aucun chunk, plutôt qu'un chunk vide.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, f"{SECTION_ARTICLES}.xml")
    )

    assert parsed.content == ""
    assert parsed.structure["sections"] == []
    assert parsed.title.startswith("Section 3")
    assert len(parsed.structure["references"]) == 14  # ses articles, eux, sont là


def test_le_parser_rend_les_liens_BRUTS_sans_les_typer(fixtures_dir: Path) -> None:
    """Le parser lit, il ne traduit pas : il rend le vocabulaire de LEGI tel quel
    (``typelien``, ``sens``). Typer ici mettrait la table de traduction dans deux
    modules à la fois — et le jour où l'un des deux dérive, les arêtes changent de sens
    sans qu'on sache lequel a raison.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    )

    (lien,) = [r for r in parsed.structure["references"] if r["kind"] == "LIEN"]
    assert lien["typelien"] == "CREE"  # le mot de LEGI, pas CREATES
    assert lien["sens"] == "cible"


def test_le_contexte_porte_la_fermeture_des_ancetres(fixtures_dir: Path) -> None:
    """``<CONTEXTE>`` déclare TOUS les ancêtres d'un coup — la fermeture transitive, pas
    le seul parent. C'est ce qui rend la réduction nécessaire en aval.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    )

    context = parsed.structure["context"]
    assert len(context) > 1, "un seul ancêtre ne serait pas une fermeture"
    assert any(c["id"].startswith("LEGITEXT") for c in context)  # le texte parent
    assert any(c["id"].startswith("LEGISCTA") for c in context)  # ses sections


def test_une_balise_inconnue_est_DECLAREE_pas_ignoree(fixtures_dir: Path) -> None:
    """Le tuyau ``unknowns`` a enfin un producteur.

    Le corpus réel ne déclenche AUCUN inconnu — le vocabulaire est saturé, et c'est le
    résultat attendu. C'est précisément pourquoi il ne peut pas prouver l'instrument :
    un test qui n'observe jamais d'inconnu ne démontre pas qu'on saurait en déclarer un.
    D'où cette fixture synthétique.
    """
    parsed = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        _raw(fixtures_dir, "unknown_vocabulary.xml")
    )

    assert parsed.unknowns == {CATEGORY_TAG: ["ZORG"]}
    assert parsed.identifier.raw == ARTICLE_INCONNU
    assert "texte parfaitement ordinaire" in parsed.content  # le reste est parsé


def test_un_xml_illisible_leve_ParseError_pas_ValidationError(
    fixtures_dir: Path,
) -> None:
    """La distinction dont le manifest dépend : une panne de LECTURE n'est pas un refus
    MÉTIER. Les confondre inscrirait un fichier corrompu sous la même raison qu'un
    document sans identifiant — et on ne saurait plus lequel des deux réparer.
    """
    with pytest.raises(ET.ParseError):
        ET.parse(fixtures_dir / "malformed.xml")

    with pytest.raises(ParseError):
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id="x",
                payload={"content": []},  # le connecteur n'a rien pu transcrire
                fetched_at=datetime.now(UTC),
                owner_id=OWNER,
            )
        )


def test_un_document_sans_identifiant_leve_ValidationError() -> None:
    """Lisible, mais irrecevable : c'est un rejet métier."""
    tree = _to_tree(ET.fromstring("<ARTICLE><META/></ARTICLE>"))

    with pytest.raises(ValidationError, match="Identifiant absent"):
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id="x",
                payload={"content": [tree]},
                fetched_at=datetime.now(UTC),
                owner_id=OWNER,
            )
        )


def test_un_identifiant_mal_forme_leve_ValidationError() -> None:
    """Sans le relais explicite, la ``pydantic.ValidationError`` échapperait au
    ``except ValidationError`` des appelants et se ferait compter comme une erreur de
    parsing — un refus métier maquillé en panne de lecture.
    """
    tree = _to_tree(ET.fromstring("<ARTICLE><ID>PAS_UN_ELI</ID></ARTICLE>"))

    with pytest.raises(ValidationError, match="Identifiant invalide"):
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id="x",
                payload={"content": [tree]},
                fetched_at=datetime.now(UTC),
                owner_id=OWNER,
            )
        )


def _kinds(references: list[dict[str, Any]]) -> set[str]:
    return {reference["kind"] for reference in references}
