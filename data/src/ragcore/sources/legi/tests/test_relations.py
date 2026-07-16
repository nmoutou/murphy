"""L'extracteur : le module qui fait exister le graphe.

L'ancienne version produisait **zéro relation** sur ce corpus — les 16 227 liens
tombaient dans un ``except ValueError: continue``. Ces tests sont ce qui empêche ce
silence de revenir.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from ragcore.core.links import CITES, CONTAINS, MODIFIES, REFERENCES
from ragcore.core.models.document import ParsedDocument, RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.enums import SourceName as _SN
from ragcore.core.models.identifiers import ELI, JorfId, OwnerId
from ragcore.core.ports.relation_extractor import BaseRelationExtractor
from ragcore.core.services.unknown_categories import (
    CATEGORY_IDENTIFIER,
    CATEGORY_SENS,
    CATEGORY_TYPELIEN,
)
from ragcore.sources.generic import GenericParser, GenericRelationExtractor
from ragcore.sources.legi.file_connector import _to_tree
from ragcore.sources.legi.table import LEGI_ROLE_TABLE

from .conftest import ARTICLE_RICHE, ARTICLE_SIMPLE, SECTION_ARTICLES

OWNER = OwnerId("u1")


def _parse(fixtures_dir: Path, *names: str) -> ParsedDocument:
    return GenericParser(LEGI_ROLE_TABLE, _SN.LEGI).parse(
        RawDocument(
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
    )


def test_lextracteur_satisfait_son_port() -> None:
    assert isinstance(
        GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI),
        BaseRelationExtractor,
    )


def test_UN_lien_donne_UNE_arete(fixtures_dir: Path) -> None:
    """L'INVARIANT du lot, et ce qui interdit le retour de ``_invert``.

    ``_invert`` ajoutait l'arête inverse **en plus** de l'originale : il doublait chaque
    relation et rendait le graphe symétrique. Une citation devenait une co-citation, et
    « A modifie B » impliquait « B modifie A ».

    L'orientation n'est pas une passe appliquée après coup : c'est une propriété établie
    à la construction, depuis ``sens``.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    liens = [r for r in document.structure["references"] if r["id"]]
    ancestors = document.structure["context"]

    assert len(result.relations) == len(liens) + len(ancestors)
    assert len(liens) == 23  # l'article riche, mesuré


def test_sens_cible_signifie_que_LAUTRE_pointe_vers_MOI(fixtures_dir: Path) -> None:
    """La preuve de l'orientation, et elle est empirique.

    L'article riche (2015) porte des liens ``sens="cible"``. Si l'orientation était
    inverse, un article de 2015 « citerait » des textes postérieurs à sa propre
    rédaction. C'est l'AUTRE qui le cite : l'arête va du lié vers moi.
    """
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
    """``MODIFIE`` et ``MODIFICATION`` donnent tous deux ``MODIFIES`` — c'est le même
    verbe, vu de ses deux bouts. Ce qui les distingue est l'orientation, pas le type.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    modifies = [r for r in result.relations if r.relation_type == MODIFIES]
    typeliens = {r.metadata["typelien"] for r in modifies}

    assert typeliens == {"MODIFIE", "MODIFICATION"}
    # Le même verbe, mais chacun orienté par SON sens : les deux arêtes ne pointent pas
    # dans la même direction.
    assert len({r.source_identifier.raw for r in modifies}) == 2


def test_le_typelien_dorigine_SURVIT_dans_les_metadonnees(fixtures_dir: Path) -> None:
    """``REFERENCES`` recouvre neuf typelien distincts. Sans cette trace, ``CODIFICATION``
    et ``CONCORDANCE`` seraient indiscernables une fois en base — on aurait traduit au
    prix d'un oubli.
    """
    document = _parse(fixtures_dir, f"{ARTICLE_RICHE}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    references = [r for r in result.relations if r.relation_type == REFERENCES]
    assert {r.metadata["typelien"] for r in references} >= {"CODIFICATION"}


def test_la_hierarchie_devient_des_aretes_CONTAINS(fixtures_dir: Path) -> None:
    """Une section CONTIENT ses articles (``LIEN_ART``), un texte ses sections. Ce type
    n'existait pas avant le lot 4 : la colonne vertébrale du corpus n'avait aucun type
    sous lequel s'écrire.
    """
    document = _parse(fixtures_dir, f"{SECTION_ARTICLES}.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    contains = [r for r in result.relations if r.relation_type == CONTAINS]
    articles = [r for r in contains if r.metadata.get("kind") == "LIEN_ART"]

    assert len(articles) == 14
    for relation in articles:
        assert relation.source_identifier.raw == SECTION_ARTICLES  # la section contient


def test_les_ancetres_du_contexte_CONTIENNENT_le_document(fixtures_dir: Path) -> None:
    """``<CONTEXTE>`` déclare la fermeture transitive : l'ancêtre contient le document,
    et l'arête va de l'ancêtre VERS lui. Orientation fixe, jamais ambiguë.
    """
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
        assert relation.relation_type == CONTAINS
        assert relation.target_identifier.raw == ARTICLE_SIMPLE  # tous le contiennent


def test_un_verbe_inconnu_ENTRE_mais_un_sens_inconnu_NON(
    fixtures_dir: Path,
) -> None:
    """LE test de l'instrument — et la distinction qui en fait tout le sel.

    Le corpus réel ne produit AUCUN inconnu : les 16 typelien sont couverts. Il ne peut
    donc pas prouver que l'instrument fonctionne — d'où cette fixture synthétique, qui
    porte 3 liens dont 2 pathologiques.

    **Les deux pathologies ne se valent pas, et c'est le cœur du contrat :**

    - ``typelien="ZORGLUB"`` — le mot est inconnu, mais il *est* un mot. L'arête est
      donc réelle : quelque chose relie bien ces deux documents, on ne sait simplement
      pas encore comment ça s'appelle. Elle **entre**, sous son nom brut. Ne pas l'écrire
      reviendrait à nier un lien que la source affirme.

    - ``sens="lateral"`` — on ne sait pas **dans quel sens** va l'arête. Ici, écrire
      quand même serait inventer : une arête mal orientée ne se distingue pas d'une arête
      juste, et elle corromprait le voisinage en silence. Elle n'entre **pas**.

    La règle qui les sépare : on ingère ce qu'on ne comprend pas, on n'invente pas ce
    qu'on ne sait pas. Les deux cas sont déclarés — l'aveu, lui, est dû dans tous les cas.
    """
    document = _parse(fixtures_dir, "unknown_vocabulary.xml")
    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    assert result.unknowns == {
        CATEGORY_TYPELIEN: ["ZORGLUB"],
        CATEGORY_SENS: ["lateral"],
    }

    verbs = {r.relation_type for r in result.relations}
    assert verbs == {CITES, "zorglub"}, (
        "le lien valide ET le verbe inconnu produisent une arête ; le sens inconnu, non"
    )

    unknown_edge = next(r for r in result.relations if r.relation_type == "zorglub")
    assert unknown_edge.metadata["typelien"] == "ZORGLUB", "l'original survit"


def test_une_cible_JORF_ne_devient_JAMAIS_un_ELI() -> None:
    """Le piège des 568 arêtes, côté extracteur.

    Le motif de l'ELI (``^[A-Z]{8}[0-9]{12}$``) ne regarde pas le préfixe :
    ``JORFTEXT000000357650`` le satisfait parfaitement. Sans routage, ces arêtes seraient
    sérialisées ``eli:JORFTEXT…`` alors que le nœud JORF s'écrit ``jorf:JORFTEXT…`` —
    elles ne matcheraient jamais rien, et aucune exception ne serait levée.
    """
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

    assert isinstance(relation.target_identifier, JorfId)
    assert relation.target_identifier.serialize() == "jorf:JORFTEXT000000357650"


def test_un_id_vide_ne_pollue_PAS_les_inconnus() -> None:
    """89 ``<LIEN id="">`` dans le corpus. Un identifiant absent n'est pas un vocabulaire
    inconnu : il n'y a rien à apprendre d'un attribut vide. Le déclarer noierait les
    vrais inconnus sous du bruit.
    """
    document = _document_with_references(
        [{"kind": "LIEN", "id": "", "typelien": "CITATION", "sens": "source"}]
    )

    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    assert result.relations == []
    assert result.unknowns == {}


def test_un_id_PRESENT_mais_illisible_est_DECLARE_pas_jete() -> None:
    """La distinction jumelle de l'`id` vide : un `id` PRÉSENT mais que la table ne sait
    pas transformer (format inattendu) n'est PAS une absence — la source a écrit une
    référence. La taire (l'ancien `except: return None`) faisait disparaître l'arête en
    silence. Elle se DÉCLARE désormais en `identifiant`, pour que le bilan la porte.
    """
    document = _document_with_references(
        [{"kind": "LIEN", "id": "GARBAGE", "typelien": "CITATION", "sens": "source"}]
    )

    result = GenericRelationExtractor(LEGI_ROLE_TABLE, SourceName.LEGI).extract(
        document
    )

    assert result.relations == [], "l'arête n'est pas inventée : la cible est illisible"
    assert result.unknowns == {CATEGORY_IDENTIFIER: ["GARBAGE"]}


def _document_with_references(references: list[dict[str, Any]]) -> ParsedDocument:
    return ParsedDocument(
        identifier=ELI(raw="LEGIARTI000000000001"),
        source=SourceName.LEGI,
        owner_id=OWNER,
        title="t",
        content="c",
        structure={"references": references, "context": [], "sections": []},
        metadata={},
        parsed_at=datetime.now(UTC),
    )
