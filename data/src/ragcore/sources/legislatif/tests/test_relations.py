"""L'extracteur de liens de LEGI, qui fait exister le graphe."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ragcore.core.links import (
    CITE,
    CODIFIE,
    CONTIENT,
    HEURISTIC_KIND,
    MODIFIE,
    SUIVI_PAR,
    VERSION_KIND,
)
from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.enums import SourceName as _SN
from ragcore.core.models.identifiers import Identifier
from ragcore.core.ports.relation_extractor import BaseRelationExtractor
from ragcore.core.services.unknown_categories import CATEGORY_LINK
from ragcore.sources.generic import GenericParser, GenericRelationExtractor, to_tree
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE

from .conftest import ARTICLE_RICHE, ARTICLE_SIMPLE, SECTION_ARTICLES


def _parse(fixtures_dir: Path, *names: str) -> ParsedDocument:
    return (
        GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        .parse(
            RawDocument(
                source=SourceName.LEGI,
                source_document_id=names[0],
                payload={
                    "content": [
                        to_tree(ET.parse(fixtures_dir / name).getroot())
                        for name in names
                    ],
                    "files": list(names),
                },
                fetched_at=datetime.now(UTC),
            )
        )
        .document
    )


def test_lextracteur_satisfait_son_port() -> None:
    assert isinstance(
        GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI),
        BaseRelationExtractor,
    )


def test_UN_lien_donne_UNE_arete(fixtures_dir: Path) -> None:
    """Un lien donne une arête, orientée à la construction depuis ``sens`` : jamais
    l'arête inverse en plus."""
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    liens = [r for r in document.structure["references"] if r["id"]]
    ancestors = document.structure["context"]
    # Seule exception : les liens de version se traitent en groupe, et un document
    # n'émet que les maillons de la chaîne qui le touchent.
    versions = [r for r in liens if r["kind"] == VERSION_KIND]
    chain = [r for r in result.relations if r.relation_type == SUIVI_PAR]

    assert len(result.relations) == len(liens) - len(versions) + len(chain) + len(
        ancestors
    )
    assert (
        len([r for r in liens if r["kind"] == "LIEN"]) == 23
    )  # l'article riche, mesuré
    assert len(versions) == 25  # sa liste <VERSIONS> complète, lui-même inclus
    assert len(chain) == 2  # et il n'en sort que ses deux maillons


def test_les_versions_forment_une_CHAINE_dans_le_sens_du_temps(
    fixtures_dir: Path,
) -> None:
    """Sur 25 versions, la chaîne n'émet que deux arêtes depuis ce document : sa
    précédente → lui, lui → sa suivante. L'auto-référence l'ancre dans la liste triée.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    chain = [r for r in result.relations if r.relation_type == SUIVI_PAR]
    edges = {
        (r.source_identifier.raw, r.target_identifier.raw): r.metadata for r in chain
    }

    # La datation de l'arête est celle de sa cible
    assert edges[("LEGIARTI000006389955", ARTICLE_RICHE)]["debut"] == "2002-01-01"
    # Lui → sa suivante, dans le sens du temps
    assert edges[(ARTICLE_RICHE, "LEGIARTI000006389957")]["debut"] == "2002-02-28"


def test_sens_cible_signifie_que_LAUTRE_pointe_vers_MOI(fixtures_dir: Path) -> None:
    """Preuve empirique : l'article (2015) porte des liens ``sens="cible"`` vers des
    textes postérieurs. C'est l'autre qui le cite."""
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    cibles = [r for r in result.relations if r.metadata.get("sens") == "cible"]
    assert cibles, "l'article riche porte des liens sens=cible"

    for relation in cibles:
        assert relation.target_identifier.raw == ARTICLE_RICHE
        assert relation.source_identifier.raw != ARTICLE_RICHE


def test_sens_source_signifie_que_JE_pointe_vers_LAUTRE(fixtures_dir: Path) -> None:
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    sources = [r for r in result.relations if r.metadata.get("sens") == "source"]
    assert sources, "l'article riche porte des liens sens=source"

    for relation in sources:
        assert relation.source_identifier.raw == ARTICLE_RICHE


def test_les_paires_actives_et_passives_partagent_leur_verbe(
    fixtures_dir: Path,
) -> None:
    """``MODIFIE`` et ``MODIFICATION`` sont le même verbe vu de ses deux bouts : seule
    l'orientation les distingue."""
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    modifie = [r for r in result.relations if r.relation_type == MODIFIE]
    typeliens = {r.metadata["typelien"] for r in modifie}

    assert typeliens == {"MODIFIE", "MODIFICATION"}
    # Le même verbe, chacun orienté par son sens
    assert len({r.source_identifier.raw for r in modifie}) == 2


def test_le_typelien_dorigine_SURVIT_dans_les_metadonnees(fixtures_dir: Path) -> None:
    """Un verbe peut recouvrir plusieurs ``typelien`` : l'original survit en
    métadonnée, sinon ils seraient indiscernables en base."""
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    codifie = [r for r in result.relations if r.relation_type == CODIFIE]
    assert {r.metadata["typelien"] for r in codifie} == {"CODIFICATION"}


def test_la_hierarchie_devient_des_aretes_CONTIENT(fixtures_dir: Path) -> None:
    """Une section contient ses articles, un texte ses sections."""
    document = _parse(fixtures_dir, f"{SECTION_ARTICLES}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    contains = [r for r in result.relations if r.relation_type == CONTIENT]
    articles = [r for r in contains if r.metadata.get("kind") == "LIEN_ART"]

    assert len(articles) == 14
    for relation in articles:
        assert relation.source_identifier.raw == SECTION_ARTICLES  # la section contient


def test_les_ancetres_du_contexte_CONTIENNENT_le_document(fixtures_dir: Path) -> None:
    """``<CONTEXTE>`` déclare la fermeture transitive : l'arête va de l'ancêtre vers le
    document."""
    document = _parse(fixtures_dir, f"{ARTICLE_SIMPLE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    ancestors = [
        r
        for r in result.relations
        if r.metadata.get("kind") in {"TITRE_TXT", "TITRE_TM"}
    ]

    assert len(ancestors) == 7
    for relation in ancestors:
        assert relation.relation_type == CONTIENT
        assert relation.target_identifier.raw == ARTICLE_SIMPLE  # tous le contiennent


def test_un_verbe_inconnu_ENTRE_mais_un_sens_inconnu_NON(
    fixtures_dir: Path,
) -> None:
    """Le corpus réel ne produit aucun inconnu : la fixture synthétique porte deux liens
    pathologiques, qui ne se valent pas.

    - ``typelien="ZORGLUB"`` : un mot inconnu, mais la source affirme le lien. L'arête
      entre, sous son nom brut, et le type est déclaré en ``links``.
    - ``sens="lateral"`` : l'orienter serait inventer, et une arête mal orientée ne se
      distingue pas d'une juste. Elle n'entre pas, et compte en ``relation.unknown``.
    """
    document = _parse(fixtures_dir, "unknown_vocabulary.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    assert result.unknowns == {CATEGORY_LINK: ["ZORGLUB"]}
    assert result.lost_links == 1

    verbs = {r.relation_type for r in result.relations}
    assert verbs == {CITE, "zorglub"}, (
        "le lien valide ET le verbe inconnu produisent une arête ; le sens inconnu, non"
    )

    unknown_edge = next(r for r in result.relations if r.relation_type == "zorglub")
    assert unknown_edge.metadata["typelien"] == "ZORGLUB", "l'original survit"


def test_une_cible_JORF_garde_son_identifiant_tel_quel() -> None:
    """Les arêtes vers JORF nomment leur cible par son identifiant brut, la clé sous
    laquelle un document JORF serait écrit."""
    document = _document_with_references(
        [
            {
                "kind": "LIEN",
                "id": "JORFTEXT000000357650",
                "typelien": "CITATION",
                "sens": "source",
            }
        ]
    )

    (relation,) = (
        GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI)
        .extract(document)
        .relations
    )

    assert relation.target_identifier.serialize() == "JORFTEXT000000357650"


def test_un_id_vide_ne_pollue_PAS_les_inconnus() -> None:
    """Un ``id`` vide n'est pas un vocabulaire inconnu : rien à apprendre d'un attribut
    vide."""
    document = _document_with_references(
        [{"kind": "LIEN", "id": "", "typelien": "CITATION", "sens": "source"}]
    )

    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    assert result.relations == []
    assert result.unknowns == {}
    assert result.lost_links == 0


def test_un_id_PRESENT_mais_illisible_est_DECLARE_pas_jete() -> None:
    """Un ``id`` présent mais illisible n'est pas une absence : la source a écrit une
    référence. Il est compté en ``relation.unknown``, pas dans les types inconnus."""
    document = _document_with_references(
        [{"kind": "LIEN", "id": "GARBAGE", "typelien": "CITATION", "sens": "source"}]
    )

    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    assert result.relations == [], "l'arête n'est pas inventée : la cible est illisible"
    assert result.unknowns == {}
    assert result.lost_links == 1


_CIBLE = "LEGIARTI000000000002"


def test_le_curseur_RETIRE_les_aretes_non_configurees_mais_pas_le_signal() -> None:
    """``skip_unconfigured`` (ADR-048) retire l'arête d'un ``typelien`` inconnu et l'arête
    heuristique ; le lien configuré reste, et le signal sort dans les deux régimes."""
    document = _document_with_references(
        [
            {"kind": "LIEN", "id": _CIBLE, "typelien": "ZORGLUB", "sens": "source"},
            {"kind": "LIEN", "id": _CIBLE, "typelien": "CITATION", "sens": "source"},
            {"kind": HEURISTIC_KIND, "id": _CIBLE, "tag": "ZORG_REF"},
        ]
    )

    def verbs(skip: bool) -> set[str]:
        extractor = GenericRelationExtractor(
            LEGI_ROLE_TABLE, SourceName.LEGI, skip_unconfigured=skip
        )
        result = extractor.extract(document)
        assert result.unknowns == {CATEGORY_LINK: ["ZORGLUB"]}
        return {r.relation_type for r in result.relations}

    assert verbs(skip=False) == {CITE, "zorglub", "zorg_ref"}
    assert verbs(skip=True) == {CITE}


def test_une_balise_heuristique_impossible_en_verbe_est_PERDUE_et_comptee() -> None:
    """La balise devient le verbe : si elle ne peut pas être un type d'arête, le lien
    est compté en ``relation.unknown``, pas inventé."""
    document = _document_with_references(
        [{"kind": HEURISTIC_KIND, "id": _CIBLE, "tag": "ZORG-REF"}]
    )

    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    assert result.relations == []
    assert result.lost_links == 1


def test_une_mort_nee_saccroche_en_branche_LATERALE_hors_chaine() -> None:
    """Une version mort-née (``etat`` en ``_MORT_NE``) n'a jamais été le droit
    applicable : hors chaîne, elle s'accroche en branche latérale à la version en
    vigueur à l'avortement. L'``etat`` sur l'arête permet de l'écarter
    (``WHERE r.etat <> 'MODIFIE_MORT_NE'``).
    """
    me = "LEGIARTI000000000001"  # l'identifiant du helper : la version en vigueur
    document = _document_with_references(
        [
            {
                "kind": VERSION_KIND,
                "id": "LEGIARTI000000000009",
                "debut": "1998-07-09",
                "fin": "2005-02-24",
                "etat": "MODIFIE",
            },
            {
                "kind": VERSION_KIND,
                "id": me,
                "debut": "2005-02-24",
                "fin": "2007-01-01",
                "etat": "MODIFIE",
            },
            {
                "kind": VERSION_KIND,
                "id": "LEGIARTI000000000002",
                "debut": "2007-01-01",
                "fin": "2006-12-08",
                "etat": "MODIFIE_MORT_NE",
            },
            {
                "kind": VERSION_KIND,
                "id": "LEGIARTI000000000003",
                "debut": "2007-01-01",
                "fin": "2010-05-08",
                "etat": "MODIFIE",
            },
        ]
    )

    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    edges = {
        (r.source_identifier.raw, r.target_identifier.raw): r.metadata
        for r in result.relations
        if r.relation_type == SUIVI_PAR
    }
    assert set(edges) == {
        ("LEGIARTI000000000009", me),  # ma précédente → moi
        (me, "LEGIARTI000000000003"),  # moi → ma suivante : la chaîne saute la mort-née
        (me, "LEGIARTI000000000002"),  # moi → ma jumelle mort-née, en latéral
    }
    assert edges[(me, "LEGIARTI000000000002")]["etat"] == "MODIFIE_MORT_NE"
    assert edges[(me, "LEGIARTI000000000003")]["etat"] == "MODIFIE"


def test_une_mort_nee_recoit_son_arete_et_nen_emet_AUCUNE() -> None:
    """Vue depuis la mort-née : son arête entrante vient de la version en vigueur à
    l'avortement, et elle n'émet rien."""
    me = "LEGIARTI000000000001"  # cette fois, le helper incarne la mort-née
    document = _document_with_references(
        [
            {
                "kind": VERSION_KIND,
                "id": "LEGIARTI000000000009",
                "debut": "2005-02-24",
                "fin": "2007-01-01",
                "etat": "MODIFIE",
            },
            {
                "kind": VERSION_KIND,
                "id": me,
                "debut": "2007-01-01",
                "fin": "2006-12-08",
                "etat": "MODIFIE_MORT_NE",
            },
            {
                "kind": VERSION_KIND,
                "id": "LEGIARTI000000000003",
                "debut": "2007-01-01",
                "fin": "2010-05-08",
                "etat": "MODIFIE",
            },
        ]
    )

    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    chain = [r for r in result.relations if r.relation_type == SUIVI_PAR]
    assert len(chain) == 1, "l'entrante, et rien d'autre"
    assert chain[0].source_identifier.raw == "LEGIARTI000000000009"
    assert chain[0].target_identifier.raw == me
    assert chain[0].metadata["etat"] == "MODIFIE_MORT_NE"


def _document_with_references(references: list[dict[str, Any]]) -> ParsedDocument:
    return ParsedDocument(
        identifier=Identifier(raw="LEGIARTI000000000001"),
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title="t",
        content="c",
        structure={"references": references, "context": [], "sections": []},
        metadata={},
        parsed_at=datetime.now(UTC),
    )
