"""Fixtures des tests LEGI : de vrais fichiers du corpus, copiés et versionnés. Aucun
test ne dépend du volume du corpus, qui peut être absent.
"""

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

ARTICLE_RICHE = "LEGIARTI000006389956"
"""6 typelien distincts, les 2 sens, 7 ancêtres, 23 liens : le cas dur."""
ARTICLE_SIMPLE = "LEGIARTI000019839772"
"""Un seul lien (CREE), du contenu textuel : le cas nominal."""
SECTION_MIXTE = "LEGISCTA000006089728"
"""STRUCTURE_TA avec LIEN_ART *et* LIEN_SECTION_TA."""
SECTION_ARTICLES = "LEGISCTA000030901863"
"""14 LIEN_ART : une section qui ne contient que des articles."""
TEXTE_DEUX_FACETTES = "LEGITEXT000033839769"
"""La fusion : deux fichiers, un seul document."""
ARTICLE_INCONNU = "LEGIARTI000099999999"
"""Synthétique : typelien ZORGLUB, sens lateral, balise <ZORG>."""

# La chaîne de contenance qui exerce la réduction : <CONTEXTE> déclare la fermeture,
# <STRUCTURE_TA> l'arbre (…143 ⊃ …127 ⊃ article). « …143 ⊃ article » doit tomber.
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
"""10 fichiers lus (la paire n'en fait qu'un), un ``versions.xml`` écarté."""


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """Une copie jetable des fixtures, sans ``malformed.xml`` : il fausserait les
    comptes de documents. Les tests qui le veulent le copient eux-mêmes."""
    for xml in FIXTURES.glob("*.xml"):
        if xml.name != "malformed.xml":
            shutil.copy(xml, tmp_path / xml.name)
    return tmp_path
