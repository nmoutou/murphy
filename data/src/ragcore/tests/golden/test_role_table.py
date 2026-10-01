"""Cliquet : une balise sans rôle casse le build.

Sans lui, une balise neuve d'un export DILA entrerait sans que personne ne décide de
son rôle. Il fige ce qu'on connaît ; l'instrument du bilan (``unknowns``) découvre, sur
un corpus neuf, ce qu'on ne connaît pas.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.sources.generic import GenericParser, Role
from ragcore.sources.generic.tree import walk
from ragcore.sources.legislatif.file_connector import LegiFileConnector
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE

FIXTURES = Path(__file__).parents[2] / "sources" / "legislatif" / "tests" / "fixtures"

# La fixture `unknown_vocabulary.xml` porte délibérément du vocabulaire inconnu : elle
# teste l'instrument, pas le cliquet, qui ne pourrait sinon jamais échouer.
_FIXTURE_PATHOLOGIQUE = "unknown_vocabulary.xml"


def _raws() -> list[RawDocument]:
    async def run() -> list[RawDocument]:
        connector = LegiFileConnector(FIXTURES)
        return [
            raw
            async for raw in connector.fetch_all()
            if not any(
                Path(f).name == _FIXTURE_PATHOLOGIQUE for f in raw.payload["files"]
            )
        ]

    return asyncio.run(run())


def _tags_without_role(raw: RawDocument) -> set[str]:
    """Les balises du document que ``LEGI_ROLE_TABLE`` ne connaît pas."""
    return {
        node["tag"]
        for facet in raw.payload["content"]
        for node in walk(facet)
        if not LEGI_ROLE_TABLE.knows(node["tag"])
    }


def test_aucune_balise_du_corpus_ne_reste_sans_role() -> None:
    """Sur un corpus sain, aucune balise sans rôle.

    Un échec dit que la source parle un mot que la table ne connaît pas : décider de son
    rôle et l'écrire dans ``LEGI_ROLE_TABLE``, jamais contourner le test. Le cliquet
    parcourt l'arbre lui-même : le signal du parse est tenu par clé, pas par balise.
    """
    orphelines: dict[str, set[str]] = {}
    parser = GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI)

    for raw in _raws():
        sans_role = _tags_without_role(raw)
        if sans_role:
            orphelines.setdefault("tag", set()).update(sans_role)
        result = parser.parse(raw)
        if result.unknown_roots:
            orphelines.setdefault("racine", set()).update(result.unknown_roots)

    assert not orphelines, (
        f"Vocabulaire sans rôle dans LEGI_ROLE_TABLE : "
        f"{ {k: sorted(v) for k, v in orphelines.items()} }. "
        "Chaque balise doit porter un rôle — sinon sa donnée entre sans être comprise."
    )


def test_le_cliquet_est_CAPABLE_d_echouer() -> None:
    """Le contre-exemple : ``<ZORG>`` est trouvée par le parcours, signalée, et ingérée
    sous sa clé chemin-complet."""

    async def run() -> RawDocument:
        async for raw in LegiFileConnector(FIXTURES).fetch_all():
            if any(Path(f).name == _FIXTURE_PATHOLOGIQUE for f in raw.payload["files"]):
                return raw
        pytest.fail(f"La fixture {_FIXTURE_PATHOLOGIQUE} est introuvable")

    raw = asyncio.run(run())
    result = GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI).parse(raw)

    assert _tags_without_role(raw) == {"ZORG"}, (
        "La balise sans rôle doit être TROUVÉE. Si elle ne l'est pas, le cliquet "
        "ci-dessus ne garde rien du tout."
    )
    assert "article_zorg" in result.unconfigured_tags, (
        "Sa valeur doit être SIGNALÉE, sous sa clé chemin-complet."
    )
    assert result.document.metadata["article_zorg"], (
        "Et INGÉRÉE (porte metadata) — routée, pas jetée."
    )


def test_chaque_balise_porte_UN_role_et_un_seul() -> None:
    """Chaque valeur est un ``Role`` : une chaîne s'y glisserait sans bruit."""
    for tag, role in LEGI_ROLE_TABLE.roles.items():
        assert isinstance(role, Role), f"{tag} porte {role!r}, qui n'est pas un Role"


def test_les_quatre_roles_sont_TOUS_utilises_par_LEGI() -> None:
    """LEGI exerce les quatre rôles : le cas d'épreuve du routage complet."""
    exerces = set(LEGI_ROLE_TABLE.roles.values())
    assert exerces == set(Role), (
        f"Rôles jamais exercés par LEGI : {set(Role) - exerces}"
    )


def test_la_table_LEGI_ne_contient_AUCUNE_logique() -> None:
    """``sources/legislatif/`` ne contient ni parser ni chunker : s'il en faut un, c'est
    la mécanique générique qu'il faut compléter."""
    modules = {
        p.name
        for p in (Path(__file__).parents[2] / "sources" / "legislatif").glob("*.py")
    }

    assert "parser.py" not in modules, (
        "Le parser est GÉNÉRIQUE : LEGI n'apporte qu'une table"
    )
    assert "chunking.py" not in modules, "Le chunker est GÉNÉRIQUE"
    assert {"table.py", "vocabulary.py", "file_connector.py"} <= modules
