"""La transcription XML → arbre : sans perte, ``None`` pour un illisible, et une racine
qui peut être un ``<ID>``.
"""

from pathlib import Path
from xml.etree import ElementTree as ET

from ragcore.sources.generic import locate_id, read_root, to_tree


class TestLaTranscriptionEstSansPerte:
    def test_les_freres_homonymes_survivent(self) -> None:
        # Un dict aurait écrasé les <LIEN> l'un sur l'autre
        root = ET.fromstring(
            "<LIENS><LIEN id='a'/><LIEN id='b'/><LIEN id='c'/></LIENS>"
        )
        tree = to_tree(root)
        assert [c["attrib"]["id"] for c in tree["children"]] == ["a", "b", "c"]

    def test_texte_et_attributs_sont_conserves(self) -> None:
        tree = to_tree(ET.fromstring("<ARTICLE num='7'>corps</ARTICLE>"))
        assert tree["tag"] == "ARTICLE"
        assert tree["attrib"] == {"num": "7"}
        assert tree["text"] == "corps"


class TestLIllisibleRendNone:
    def test_un_xml_malforme_rend_none(self, tmp_path: Path) -> None:
        bad = tmp_path / "casse.xml"
        bad.write_text("<ARTICLE><non-ferme>", encoding="utf-8")
        assert read_root(bad) is None

    def test_un_xml_valide_rend_sa_racine(self, tmp_path: Path) -> None:
        good = tmp_path / "ok.xml"
        good.write_text("<ARTICLE/>", encoding="utf-8")
        root = read_root(good)
        assert root is not None
        assert root.tag == "ARTICLE"


class TestLocaliserLId:
    def test_id_enfoui_dans_l_arbre(self) -> None:
        root = ET.fromstring("<ARTICLE><META><ID>LEGI42</ID></META></ARTICLE>")
        assert locate_id(root) == "LEGI42"

    def test_la_racine_est_elle_meme_un_id(self) -> None:
        # Résidu d'export LEGI : un fichier réduit à <ID>…</ID>
        assert locate_id(ET.fromstring("<ID>NU_ID</ID>")) == "NU_ID"

    def test_pas_d_id_rend_none(self) -> None:
        assert locate_id(ET.fromstring("<ARTICLE/>")) is None

    def test_id_vide_rend_none(self) -> None:
        assert locate_id(ET.fromstring("<ARTICLE><ID>   </ID></ARTICLE>")) is None
