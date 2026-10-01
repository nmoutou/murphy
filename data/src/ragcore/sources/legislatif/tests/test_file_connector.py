"""Le connecteur LEGI : ce qu'il émet, ce qu'il fusionne, ce qu'il écarte."""

import inspect
from pathlib import Path

import pytest

from ragcore.core.ports.connector import BaseConnector
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_UNREADABLE,
)
from ragcore.sources.legislatif.file_connector import LegiFileConnector

from .conftest import (
    ARTICLE_RICHE,
    ARTICLE_SIMPLE,
    DOCUMENTS,
    TEXTE_DEUX_FACETTES,
)


async def _collect(connector: LegiFileConnector) -> dict[str, object]:
    return {doc.source_document_id: doc async for doc in connector.fetch_all()}


def test_le_connecteur_satisfait_son_port() -> None:
    """Typage structurel : ``isinstance`` est la seule preuve exécutable de
    substituabilité."""
    assert isinstance(LegiFileConnector(Path(".")), BaseConnector)


@pytest.mark.asyncio
async def test_fetch_all_est_un_generateur(corpus: Path) -> None:
    """Un générateur, pas une liste : le corpus ne tient pas en mémoire."""
    assert inspect.isasyncgen(LegiFileConnector(corpus).fetch_all())


@pytest.mark.asyncio
async def test_les_deux_facettes_dun_texte_ne_font_QUUN_document(corpus: Path) -> None:
    """``TEXTE_VERSION`` et ``TEXTELR`` partagent leur ``<ID>`` : émises séparément,
    la facette sans titre écraserait l'autre."""
    docs = await _collect(LegiFileConnector(corpus))

    assert TEXTE_DEUX_FACETTES in docs
    facets = docs[TEXTE_DEUX_FACETTES].payload["content"]
    assert len(facets) == 2, "les deux facettes doivent voyager ensemble"

    roots = {facet["tag"] for facet in facets}
    assert roots == {"TEXTE_VERSION", "TEXTELR"}


@pytest.mark.asyncio
async def test_un_document_par_identifiant_pas_par_fichier(corpus: Path) -> None:
    """11 fichiers, 9 documents : ``versions.xml`` est écarté, et les deux facettes du
    texte n'en font qu'un."""
    docs = await _collect(LegiFileConnector(corpus))

    assert set(docs) == DOCUMENTS


@pytest.mark.asyncio
async def test_lartefact_dexport_est_ecarte_ET_compte(corpus: Path) -> None:
    """Les ``versions.xml`` sont écartés, et comptés."""
    connector = LegiFileConnector(corpus)
    docs = await _collect(connector)

    assert connector.skipped == {REASON_EXPORT_ARTIFACT: 1}
    assert not any("JORFCONT" in doc_id for doc_id in docs)


@pytest.mark.asyncio
async def test_un_xml_illisible_est_ecarte_ET_compte(tmp_path: Path) -> None:
    """Un XML qui ne parse pas est écarté et compté (``unreadable``), avant
    ``document.fetched``."""
    (tmp_path / "malformed.xml").write_text(
        "<ARTICLE><META><ID>LEGIARTI000000000042</ID>",  # jamais refermé
        encoding="utf-8",
    )

    connector = LegiFileConnector(tmp_path)
    docs = await _collect(connector)

    assert docs == {}
    assert connector.skipped == {REASON_UNREADABLE: 1}


@pytest.mark.asyncio
async def test_on_ecarte_sur_la_racine_pas_sur_le_nom(tmp_path: Path) -> None:
    """Un ``versions.xml`` de racine ``<ARTICLE>`` est un document : jamais d'écart sur
    le seul nom."""
    (tmp_path / "versions.xml").write_text(
        '<?xml version="1.0"?>'
        "<ARTICLE><META><META_COMMUN><ID>LEGIARTI000000000042</ID>"
        "</META_COMMUN></META></ARTICLE>",
        encoding="utf-8",
    )

    connector = LegiFileConnector(tmp_path)
    docs = await _collect(connector)

    assert set(docs) == {"LEGIARTI000000000042"}
    assert connector.skipped == {}


@pytest.mark.asyncio
async def test_les_liens_freres_survivent_a_la_transcription(corpus: Path) -> None:
    """Sans perte : les 23 ``<LIEN>`` frères survivent, les enfants étant une liste."""
    docs = await _collect(LegiFileConnector(corpus))
    (tree,) = docs[ARTICLE_RICHE].payload["content"]

    liens = _find_all(tree, "LIEN")
    assert len(liens) == 23
    assert {lien["attrib"]["typelien"] for lien in liens} >= {"CITATION", "MODIFIE"}


@pytest.mark.asyncio
async def test_le_connecteur_ninterprete_rien(corpus: Path) -> None:
    """Le payload ne porte aucune sémantique LEGI : l'arbre et son fichier, rien de
    plus."""
    docs = await _collect(LegiFileConnector(corpus))
    payload = docs[ARTICLE_SIMPLE].payload

    assert set(payload) == {"content", "files"}
    (tree,) = payload["content"]
    assert set(tree) == {"tag", "attrib", "text", "tail", "children"}


def _find_all(tree: dict, tag: str) -> list[dict]:
    found = [tree] if tree["tag"] == tag else []
    for child in tree["children"]:
        found.extend(_find_all(child, tag))
    return found
