"""Fixtures partagées des tests LEGI.

**Le corpus réel est une source de FIXTURES, jamais une DÉPENDANCE de test.** Les
XML de ``fixtures/`` sont de vrais fichiers du corpus, copiés et versionnés. Aucun
test ne touche ``/mnt/data/Murphy/src/LEGI`` : ce volume peut être absent (CI, autre
machine), et une suite qui en dépendrait ne prouverait rien là où elle ne tourne pas.
"""

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Les identifiants des fixtures, nommés une fois pour toutes. Les tests s'y réfèrent
# par ces constantes : un ELI en dur dans une assertion est illisible six mois plus tard.
ARTICLE_RICHE = "LEGIARTI000006389956"
"""6 typelien distincts, les 2 sens, 7 ancêtres, 23 liens. Le cas dur."""
ARTICLE_SIMPLE = "LEGIARTI000019839772"
"""Un seul lien (CREE), du contenu textuel. Le cas nominal."""
SECTION_MIXTE = "LEGISCTA000006089728"
"""STRUCTURE_TA avec LIEN_ART *et* LIEN_SECTION_TA."""
SECTION_ARTICLES = "LEGISCTA000030901863"
"""14 LIEN_ART — une section qui ne contient que des articles."""
TEXTE_DEUX_FACETTES = "LEGITEXT000033839769"
"""LE cas de la fusion : deux fichiers, un seul document."""
ARTICLE_INCONNU = "LEGIARTI000099999999"
"""Synthétique : typelien ZORGLUB, sens lateral, balise <ZORG>."""

# La chaîne de contenance — le seul trio qui exerce vraiment la réduction transitive.
# Le <CONTEXTE> de l'article déclare la FERMETURE (les deux sections le contiennent) ;
# les <STRUCTURE_TA> déclarent l'ARBRE (…143 ⊃ …127 ⊃ article). L'arête directe
# « …143 ⊃ article » est donc redondante avec le chemin, et doit tomber.
ARTICLE_HIERARCHISE = "LEGIARTI000045328204"
SECTION_PARENTE = "LEGISCTA000045328127"
SECTION_GRAND_PARENTE = "LEGISCTA000045328143"

DOCUMENTS = frozenset(
    {
        ARTICLE_RICHE,
        ARTICLE_SIMPLE,
        SECTION_MIXTE,
        SECTION_ARTICLES,
        TEXTE_DEUX_FACETTES,
        ARTICLE_INCONNU,
        ARTICLE_HIERARCHISE,
        SECTION_PARENTE,
        SECTION_GRAND_PARENTE,
    }
)
"""Les 9 documents du corpus de test — pour 10 fichiers lus (la paire n'en fait qu'un) et
un ``versions.xml`` écarté."""


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """Une copie jetable des fixtures — sans ``malformed.xml``.

    Le XML illisible est exclu du corpus par défaut : il ferait échouer les tests qui
    comptent les documents, alors qu'il n'existe que pour prouver la distinction
    ``ParseError`` / ``ValidationError`` du parser. Les tests qui le veulent le
    copient eux-mêmes.
    """
    for xml in FIXTURES.glob("*.xml"):
        if xml.name != "malformed.xml":
            shutil.copy(xml, tmp_path / xml.name)
    return tmp_path
