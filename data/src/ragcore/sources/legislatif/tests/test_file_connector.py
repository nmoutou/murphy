"""Le connecteur LEGI : ce qu'il émet, ce qu'il fusionne, ce qu'il écarte."""

import inspect
import os
from pathlib import Path

import pytest

from ragcore.core.models.enums import SourceName
from ragcore.core.models.inventory import SourceInventory
from ragcore.core.ports.connector import BaseConnector
from ragcore.core.services.collision_reasons import COLLISION_SUPERSEDED_COPY
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_ID_MISMATCH,
    REASON_UNREADABLE,
)
from ragcore.sources.legislatif.file_connector import LegiFileConnector
from ragcore.tests.fakes import read_source

from .conftest import (
    ARTICLE_RICHE,
    ARTICLE_SIMPLE,
    DOCUMENTS,
    TEXTE_DEUX_FACETTES,
)

_ARTICLE_42 = "LEGIARTI000000000042"


def _collect(connector: LegiFileConnector) -> dict[str, object]:
    return {doc.source_document_id: doc for doc in read_source(connector)}


def _write_article(path: Path, identifier: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<?xml version="1.0"?>'
        f"<ARTICLE><META><META_COMMUN><ID>{identifier}</ID>"
        "</META_COMMUN></META></ARTICLE>",
        encoding="utf-8",
    )


def test_le_connecteur_satisfait_son_port() -> None:
    """Typage structurel : ``isinstance`` est la seule preuve exécutable de
    substituabilité."""
    assert isinstance(LegiFileConnector(Path(".")), BaseConnector)


def test_la_passe_1_compte_les_cles_sans_les_artefacts(corpus: Path) -> None:
    """Les deux facettes du texte font une clé, et les ``versions.xml`` sont mis à
    part."""
    inventory = LegiFileConnector(corpus).discover()

    assert inventory == {
        SourceName.LEGI: SourceInventory(total=len(DOCUMENTS), retained=len(DOCUMENTS))
    }


def test_un_ratio_reduit_n_emet_que_les_cles_retenues(corpus: Path) -> None:
    """Choisies avant toute lecture ; les facettes d'une clé retenue voyagent
    ensemble, et les artefacts d'export sont toujours écartés."""
    connector = LegiFileConnector(corpus, ingestion_ratio=0.5)

    (inventory,) = connector.discover().values()
    docs = {doc.source_document_id: doc for doc in connector.fetch_all()}

    assert inventory == SourceInventory(total=9, retained=5, ratio=0.5)
    assert len(docs) == 5
    assert set(docs) < DOCUMENTS
    assert connector.skipped == {REASON_EXPORT_ARTIFACT: 1}


def test_fetch_all_est_un_generateur(corpus: Path) -> None:
    """Un générateur, pas une liste : le corpus ne tient pas en mémoire."""
    connector = LegiFileConnector(corpus)
    connector.discover()

    assert inspect.isgenerator(connector.fetch_all())


def test_fetch_all_sans_passe_1_leve(corpus: Path) -> None:
    with pytest.raises(RuntimeError, match="discover"):
        next(LegiFileConnector(corpus).fetch_all())


def test_les_deux_facettes_dun_texte_ne_font_QUUN_document(corpus: Path) -> None:
    """``TEXTE_VERSION`` et ``TEXTELR`` partagent leur ``<ID>``, dans deux dossiers :
    émises séparément, la facette sans titre écraserait l'autre."""
    docs = _collect(LegiFileConnector(corpus))

    assert TEXTE_DEUX_FACETTES in docs
    facets = docs[TEXTE_DEUX_FACETTES].payload["content"]
    assert len(facets) == 2, "les deux facettes doivent voyager ensemble"

    roots = {facet["tag"] for facet in facets}
    assert roots == {"TEXTE_VERSION", "TEXTELR"}


def test_un_document_par_identifiant_pas_par_fichier(corpus: Path) -> None:
    """11 fichiers, 9 documents : ``versions.xml`` est écarté, et les deux facettes du
    texte n'en font qu'un."""
    docs = _collect(LegiFileConnector(corpus))

    assert set(docs) == DOCUMENTS


def test_lartefact_dexport_est_ecarte_ET_compte(corpus: Path) -> None:
    """Les ``versions.xml`` sont écartés, et comptés."""
    connector = LegiFileConnector(corpus)
    docs = _collect(connector)

    assert connector.skipped == {REASON_EXPORT_ARTIFACT: 1}
    assert not any("JORFCONT" in doc_id for doc_id in docs)


def test_un_xml_illisible_est_ecarte_ET_compte(tmp_path: Path) -> None:
    """Un XML qui ne parse pas est écarté et compté (``unreadable``), avant
    ``document.fetched``."""
    (tmp_path / f"{_ARTICLE_42}.xml").write_text(
        f"<ARTICLE><META><ID>{_ARTICLE_42}</ID>",  # jamais refermé
        encoding="utf-8",
    )

    connector = LegiFileConnector(tmp_path)
    docs = _collect(connector)

    assert docs == {}
    assert connector.skipped == {REASON_UNREADABLE: 1}


def test_une_facette_illisible_n_emporte_pas_l_autre(tmp_path: Path) -> None:
    _write_article(tmp_path / "en_vigueur" / f"{_ARTICLE_42}.xml", _ARTICLE_42)
    broken = tmp_path / "non_vigueur" / f"{_ARTICLE_42}.xml"
    broken.parent.mkdir()
    broken.write_text("<ARTICLE>", encoding="utf-8")

    connector = LegiFileConnector(tmp_path)
    docs = _collect(connector)

    assert len(docs[_ARTICLE_42].payload["files"]) == 1
    assert connector.skipped == {REASON_UNREADABLE: 1}


def test_la_copie_la_plus_recente_d_un_article_fait_foi(tmp_path: Path) -> None:
    """L'export garde la copie périmée dans l'autre arborescence : seule la plus
    récente est émise, et l'arbitrage est une collision."""
    stale = tmp_path / "en_vigueur" / f"{_ARTICLE_42}.xml"
    fresh = tmp_path / "non_vigueur" / f"{_ARTICLE_42}.xml"
    _write_article(stale, _ARTICLE_42)
    fresh.parent.mkdir()
    fresh.write_text(
        stale.read_text(encoding="utf-8").replace("<META>", "<META><ETAT/>"),
        encoding="utf-8",
    )
    os.utime(stale, ns=(1_000, 1_000))
    os.utime(fresh, ns=(2_000, 2_000))

    connector = LegiFileConnector(tmp_path)
    docs = _collect(connector)

    assert docs[_ARTICLE_42].payload["files"] == [str(fresh)]
    (collision,) = connector.collisions
    assert collision.reason == COLLISION_SUPERSEDED_COPY
    assert collision.files == (str(fresh), str(stale))
    assert connector.skipped == {}


def test_un_fichier_dont_l_ID_n_est_pas_le_nom_est_ecarte_ET_compte(
    tmp_path: Path,
) -> None:
    """La clé du flux est le nom : émis sous une autre clé que son identifiant, le
    document pourrait croiser son jumeau dans un autre worker."""
    _write_article(tmp_path / "LEGIARTI000000000043.xml", _ARTICLE_42)

    connector = LegiFileConnector(tmp_path)
    docs = _collect(connector)

    assert docs == {}
    assert connector.skipped == {REASON_ID_MISMATCH: 1}


@pytest.mark.parametrize(
    "content", ["<VERSIONS><VERSION/></VERSIONS>", "<ID>JORFCONT000029958086</ID>"]
)
def test_les_deux_formes_de_l_artefact_sont_ecartees(
    tmp_path: Path, content: str
) -> None:
    (tmp_path / "versions.xml").write_text(content, encoding="utf-8")

    connector = LegiFileConnector(tmp_path)
    _collect(connector)

    assert connector.skipped == {REASON_EXPORT_ARTIFACT: 1}


def test_un_versions_xml_qui_n_est_pas_un_artefact_est_REJETE(tmp_path: Path) -> None:
    """Sa clé, ``versions``, n'est jamais son ``<ID>`` : rejeté, pas ingéré."""
    _write_article(tmp_path / "versions.xml", _ARTICLE_42)

    connector = LegiFileConnector(tmp_path)
    docs = _collect(connector)

    assert docs == {}
    assert connector.skipped == {REASON_ID_MISMATCH: 1}


def test_les_liens_freres_survivent_a_la_transcription(corpus: Path) -> None:
    """Sans perte : les 23 ``<LIEN>`` frères survivent, les enfants étant une liste."""
    docs = _collect(LegiFileConnector(corpus))
    (tree,) = docs[ARTICLE_RICHE].payload["content"]

    liens = _find_all(tree, "LIEN")
    assert len(liens) == 23
    assert {lien["attrib"]["typelien"] for lien in liens} >= {"CITATION", "MODIFIE"}


def test_le_connecteur_ninterprete_rien(corpus: Path) -> None:
    """Le payload ne porte aucune sémantique LEGI : l'arbre et son fichier, rien de
    plus."""
    docs = _collect(LegiFileConnector(corpus))
    payload = docs[ARTICLE_SIMPLE].payload

    assert set(payload) == {"content", "files"}
    (tree,) = payload["content"]
    assert set(tree) == {"tag", "attrib", "text", "tail", "children"}


def _find_all(tree: dict, tag: str) -> list[dict]:
    found = [tree] if tree["tag"] == tag else []
    for child in tree["children"]:
        found.extend(_find_all(child, tag))
    return found
