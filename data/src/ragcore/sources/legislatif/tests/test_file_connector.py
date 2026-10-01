"""Le connecteur : ce qu'il émet, ce qu'il fusionne, ce qu'il écarte."""

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
    """Typage structurel : rien n'hérite de ``BaseConnector``. ``isinstance`` est la
    SEULE preuve exécutable de substituabilité — sans elle, rien ne la vérifierait.
    """
    assert isinstance(LegiFileConnector(Path(".")), BaseConnector)


@pytest.mark.asyncio
async def test_fetch_all_est_un_generateur(corpus: Path) -> None:
    """Le corpus fait 2564 fichiers. Un ``list`` en retour le chargerait entièrement en
    mémoire — le port dit explicitement un ``AsyncIterator``.
    """
    assert inspect.isasyncgen(LegiFileConnector(corpus).fetch_all())


@pytest.mark.asyncio
async def test_les_deux_facettes_dun_texte_ne_font_QUUN_document(corpus: Path) -> None:
    """LE test du connecteur.

    ``TEXTE_VERSION`` et ``TEXTELR`` portent le MÊME ``<ID>`` (mesuré : 98/98 sur le
    corpus). Un ``RawDocument`` par fichier, et le second — celui qui n'a pas de titre —
    écraserait le premier dans Mongo. Les 98 textes du corpus finiraient sans titre,
    sans qu'aucune exception ne soit levée.
    """
    docs = await _collect(LegiFileConnector(corpus))

    assert TEXTE_DEUX_FACETTES in docs
    facets = docs[TEXTE_DEUX_FACETTES].payload["content"]
    assert len(facets) == 2, "les deux facettes doivent voyager ensemble"

    roots = {facet["tag"] for facet in facets}
    assert roots == {"TEXTE_VERSION", "TEXTELR"}


@pytest.mark.asyncio
async def test_un_document_par_identifiant_pas_par_fichier(corpus: Path) -> None:
    """11 fichiers dans le corpus de test, mais 9 documents : ``versions.xml`` est écarté,
    et les deux facettes du texte n'en font qu'un.
    """
    docs = await _collect(LegiFileConnector(corpus))

    assert set(docs) == DOCUMENTS


@pytest.mark.asyncio
async def test_lartefact_dexport_est_ecarte_ET_compte(corpus: Path) -> None:
    """1637 des 2564 fichiers du corpus sont des ``versions.xml`` : un ID nu, rien
    d'autre. Les passer au parser produirait 1637 rejets qui noieraient les vrais.

    Mais écarter n'est PAS taire : le compte est ce qui distingue « ignoré » de
    « caché ».
    """
    connector = LegiFileConnector(corpus)
    docs = await _collect(connector)

    assert connector.skipped == {REASON_EXPORT_ARTIFACT: 1}
    assert not any("JORFCONT" in doc_id for doc_id in docs)


@pytest.mark.asyncio
async def test_un_xml_illisible_est_ecarte_ET_compte(tmp_path: Path) -> None:
    """Un XML qui ne parse pas (tronqué, corrompu) n'a pas d'arbre à transcrire.

    L'ancien code le ``continue``-ait en silence : le fichier disparaissait AVANT
    ``document.fetched``, donc hors de l'équation de complétude — une perte que rien
    ne signalait. Il est désormais écarté EN ÉTANT COMPTÉ (``unreadable``).
    """
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
    """Le garde-fou. Un fichier NOMMÉ ``versions.xml`` mais dont la racine est
    ``<ARTICLE>`` est un document, et il doit être émis.

    Écarter sur le seul nom, ce serait ériger une convention de nommage en règle
    métier — et perdre des documents le jour où l'export la change.
    """
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
    """La transcription doit être SANS PERTE. L'article riche porte 23 ``<LIEN>`` frères ;
    un dict à plat les aurait écrasés l'un sur l'autre et il n'en resterait qu'un. C'est
    pourquoi le connecteur rend un ARBRE, dont les enfants sont une liste.
    """
    docs = await _collect(LegiFileConnector(corpus))
    (tree,) = docs[ARTICLE_RICHE].payload["content"]

    liens = _find_all(tree, "LIEN")
    assert len(liens) == 23
    assert {lien["attrib"]["typelien"] for lien in liens} >= {"CITATION", "MODIFIE"}


@pytest.mark.asyncio
async def test_le_connecteur_ninterprete_rien(corpus: Path) -> None:
    """Le payload ne contient aucune sémantique LEGI : ni ELI construit, ni relation
    extraite, ni contenu nettoyé. Juste l'arbre, et d'où il vient. Tout le reste est
    le métier du parser.
    """
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
