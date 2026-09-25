"""La transcription XML → arbre — **générique par nature, donc ici et pas ailleurs.**

Lire un fichier XML, le transcrire en dict-arbre sans perte, y localiser l'``<ID>`` :
aucun de ces trois gestes ne connaît LEGI ni la jurisprudence. Ils faisaient pourtant
double emploi — la juri importait le ``_to_tree`` *privé* de legi (un couplage inter-
sources que rien ne justifiait) et recopiait ``_read``/``_locate_id`` à l'identique.

Ce module est le foyer unique de cette mécanique. Un connecteur de source y puise, et
n'écrit plus que ce qui lui est propre : ce qu'il écarte, et comment il groupe.

**« Sans perte » est le critère.** Les enfants sont une LISTE — c'est ce qui préserve les
frères homonymes (les 23 ``<LIEN>`` d'un même article) qu'un dict aurait écrasés l'un sur
l'autre. Aplatir serait déjà interpréter ; ce module ne le fait jamais.
"""

from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

__all__ = ["locate_id", "read_root", "to_tree"]


def read_root(path: Path) -> ET.Element | None:
    """Lit un fichier XML et rend sa racine — ou ``None`` s'il est illisible.

    ``None`` n'est pas une erreur silencieuse : c'est un signal que l'appelant DOIT
    compter (``skipped[REASON_UNREADABLE]``). Écarter sans compter serait un skip caché,
    et un fichier illisible qui disparaît avant ``seen`` est une perte invisible à
    l'équation de complétude.
    """
    try:
        return ET.parse(path).getroot()  # noqa: S314 — corpus local, pas une entrée réseau
    except ET.ParseError:
        return None


def to_tree(element: ET.Element) -> dict[str, Any]:
    """XML → dict, mécaniquement. Zéro sémantique, zéro perte.

    Les enfants sont une LISTE : c'est ce qui préserve les frères homonymes (les 23
    ``<LIEN>`` d'un même article) qu'un dict aurait écrasés l'un sur l'autre.
    """
    return {
        "tag": element.tag,
        "attrib": dict(element.attrib),
        "text": element.text or "",
        "tail": element.tail or "",
        "children": [to_tree(child) for child in element],
    }


def locate_id(element: ET.Element) -> str | None:
    """Le premier ``<ID>`` de l'arbre — le seul acte de « lecture » du connecteur.

    Ce n'est pas interpréter : il ne valide rien, ne construit aucun identifiant, ne juge
    pas du format. Le connecteur a besoin d'une CLÉ pour nommer (ou grouper) un
    ``RawDocument`` ; le parser, lui, en fera un identifiant — et le rejettera s'il est
    mal formé.

    On gère le cas où la racine EST l'``<ID>`` : certains résidus d'export LEGI sont des
    fichiers d'une ligne réduits à ``<ID>…</ID>``, et le connecteur doit pouvoir les
    localiser pour les écarter.
    """
    if element.tag == "ID":
        return (element.text or "").strip() or None
    found = element.find(".//ID")
    if found is None:
        return None
    return (found.text or "").strip() or None
