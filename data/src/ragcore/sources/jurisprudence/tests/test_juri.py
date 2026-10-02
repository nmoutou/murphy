"""La jurisprudence, sur des extraits littéraux du corpus, copiés ici exprès : le
corpus n'est jamais une dépendance de test.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ragcore.core.links import CITE, LinkSubject, extract_links
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.ports.parser import ParseResult
from ragcore.sources.generic import GenericParser
from ragcore.sources.generic.tree import walk
from ragcore.sources.jurisprudence import (
    JURI_ADMIN_ROLE_TABLE,
    JURI_CONSTIT_ROLE_TABLE,
    JURI_JUDI_ROLE_TABLE,
    JURI_LINK_TABLE,
    ROLE_TABLE_BY_ROOT,
    JuriFileConnector,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _raw(name: str, source: SourceName) -> RawDocument:
    async def run() -> RawDocument:
        connector = JuriFileConnector(FIXTURES, source)
        async for raw in connector.fetch_all():
            if Path(raw.payload["files"][0]).name == name:
                return raw
        pytest.fail(f"Fixture introuvable : {name}")

    return asyncio.run(run())


def _parse_result(raw: RawDocument, source: SourceName) -> ParseResult:
    root = raw.payload["content"][0]["tag"]
    return GenericParser(ROLE_TABLE_BY_ROOT[root], source).parse(raw)


def _parse(name: str, source: SourceName):
    return _parse_result(_raw(name, source), source).document


def test_une_citation_decrite_devient_une_RELATION_NON_FORMATEE_jamais_une_arete() -> (
    None
):
    """Les ``<LIEN>`` juri n'ont aucun attribut, seulement un texte (« Articles 1103 et
    1229 du code civil ») : ils entrent comme relations non formatées, pas comme arêtes
    ni comme nœuds."""
    document = _parse("cass_avec_liens.xml", SourceName.CASS)

    links = extract_links(
        references=document.structure["references"],
        ancestors=document.structure["context"],
        table=JURI_LINK_TABLE,
        subject=LinkSubject(current=document.identifier, source=SourceName.CASS),
    )

    assert not links.relations, (
        "une cible DÉCRITE ne produit aucune arête — c'est tout le changement"
    )
    assert links.unformatted_relations, "…mais elle n'est pas perdue pour autant"

    unformatted = links.unformatted_relations[0]
    assert unformatted.source_identifier == document.identifier, (
        "elle sait quel document l'énonce : elle ne vit plus sur lui"
    )
    assert unformatted.source == SourceName.CASS
    assert unformatted.relation_type == CITE, "le verbe traduit survit"
    assert unformatted.sens == "source", (
        "le sens aussi : c'est lui qui orientera l'arête le jour de la résolution"
    )
    assert "loi n° 75-1334" in unformatted.target_text, (
        "et la PHRASE est intacte : c'est elle que la passe de résolution lira pour "
        "retrouver le vrai article"
    )


def test_un_arret_est_nomme_par_son_identifiant_brut() -> None:
    """Un arrêt se distingue par le préfixe de son identifiant (``JURITEXT``)."""
    document = _parse("cass_avec_liens.xml", SourceName.CASS)

    assert document.identifier.prefix == "JURITEXT"
    assert document.identifier.serialize() == document.identifier.raw


def test_la_juri_n_a_AUCUNE_balise_sans_role() -> None:
    """Cliquet : aucune balise sans rôle sur les fixtures des trois tables. Le cliquet
    parcourt l'arbre lui-même : le signal du parse est tenu par clé, pas par balise.
    """
    orphelines: dict[str, set[str]] = {}

    for fixture, source, table in (
        ("cass_avec_liens.xml", SourceName.CASS, JURI_JUDI_ROLE_TABLE),
        ("jade.xml", SourceName.JADE, JURI_ADMIN_ROLE_TABLE),
        ("constit.xml", SourceName.CONSTIT, JURI_CONSTIT_ROLE_TABLE),
    ):
        raw = _raw(fixture, source)
        sans_role = {
            node["tag"]
            for facet in raw.payload["content"]
            for node in walk(facet)
            if not table.knows(node["tag"])
        }
        if sans_role:
            orphelines.setdefault("tag", set()).update(sans_role)
        result = _parse_result(raw, source)
        if result.unknown_roots:
            orphelines.setdefault("racine", set()).update(result.unknown_roots)

    assert not orphelines, (
        f"Vocabulaire sans rôle dans les tables juri : "
        f"{ {k: sorted(v) for k, v in orphelines.items()} }"
    )


def test_les_trois_racines_ont_leur_table() -> None:
    """CAPP, CASS et INCA publient la même racine : une table par forme de document,
    pas par base."""
    assert set(ROLE_TABLE_BY_ROOT) == {
        "TEXTE_JURI_JUDI",
        "TEXTE_JURI_ADMIN",
        "TEXTE_JURI_CONSTIT",
    }
    assert (
        ROLE_TABLE_BY_ROOT["TEXTE_JURI_JUDI"] is ROLE_TABLE_BY_ROOT["TEXTE_JURI_JUDI"]
    )


def test_la_juri_n_a_AUCUN_role_version() -> None:
    """Un arrêt est rendu une fois : aucune balise ``VERSION``."""
    for table in ROLE_TABLE_BY_ROOT.values():
        assert table.version_tags == frozenset(), (
            "la juri n'a pas d'axe temporel — aucune balise de datation de version"
        )


def test_le_contenu_de_larret_est_ingere() -> None:
    """Le texte est bien là : des arêtes sans contenu passeraient sinon inaperçues."""
    document = _parse("cass_avec_liens.xml", SourceName.CASS)

    assert document.content.strip(), "l'arrêt DOIT avoir du texte"
    assert document.title.strip()
    assert document.metadata.get("juridiction")


@pytest.mark.parametrize(
    ("fixture", "source", "nature"),
    [
        ("cass_avec_liens.xml", SourceName.CASS, "ARRET"),
        # JADE écrit « Texte » pour toutes ses décisions
        ("jade.xml", SourceName.JADE, None),
        ("constit.xml", SourceName.CONSTIT, "QPC"),
    ],
)
def test_toute_decision_est_typee_DECISION_avec_sa_nature(
    fixture: str, source: SourceName, nature: str | None
) -> None:
    document = _parse(fixture, source)

    assert document.document_type == DocumentType.DECISION
    assert document.nature == nature
    assert not {"nature", "type_document"} & document.metadata.keys()
