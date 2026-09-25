"""CLIQUET — **une balise sans rôle casse le build** (§3).

C'est le dispositif que la doctrine réclame nommément, et le jumeau exact du catalogue
d'events (§12) : *rien n'entre en silence*.

**Le danger qu'il garde.** LEGI publie un export ; une balise neuve apparaît. Sans ce
cliquet, elle traverse le parser sans un mot : son texte n'est ni du corps, ni une
métadonnée, ni un lien — il **disparaît**. Aucune exception, aucun log, un corpus
silencieusement amputé. C'est précisément la forme du bug qui a fait s'évaporer 16 227
liens pendant des mois.

Avec lui, la balise ressort dans ``ParseResult.unconfigured_tags``, ce test échoue, et
quelqu'un doit **décider** de son rôle. La décision peut être « c'est du bruit, rôle
META » — mais elle est prise, et écrite. Depuis le cadrage « trois portes » (B-00-d),
la donnée de la balise n'attend plus la décision : elle entre en métadonnée (clé
chemin-complet) ou en lien (heuristique DILA) — le signal, lui, réclame toujours la
décision.

**Le cliquet et l'instrument sont complémentaires**, et il faut les distinguer :

- Le cliquet (ici) fige ce qu'on connaît : sur les fixtures, le signal doit être VIDE.
- L'instrument (``tag.unconfigured`` → ``RunStats.unknowns`` → ``RunSummary``) découvre
  ce qu'on ne connaît pas : sur un corpus neuf, la balise remonte dans le bilan du run.

Le premier interdit la régression ; le second permet la saturation. Ni l'un ni l'autre
seul ne suffit.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId
from ragcore.sources.generic import GenericParser, Role
from ragcore.sources.legi.file_connector import LegiFileConnector
from ragcore.sources.legi.table import LEGI_ROLE_TABLE

FIXTURES = Path(__file__).parents[2] / "sources" / "legi" / "tests" / "fixtures"
OWNER = OwnerId("u1")

# La fixture `unknown_vocabulary.xml` porte DÉLIBÉRÉMENT du vocabulaire inconnu : une
# balise <ZORG> et un typelien ZORGLUB. C'est l'instrument qu'elle teste, pas le cliquet
# — et les mélanger rendrait le cliquet incapable d'échouer.
_FIXTURE_PATHOLOGIQUE = "unknown_vocabulary.xml"


def _parse_all() -> list:
    async def run() -> list:
        parser = GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI)
        connector = LegiFileConnector(FIXTURES)
        return [
            parser.parse(raw)
            async for raw in connector.fetch_all(OWNER)
            if not any(
                Path(f).name == _FIXTURE_PATHOLOGIQUE for f in raw.payload["files"]
            )
        ]

    return asyncio.run(run())


def test_aucune_balise_du_corpus_ne_reste_sans_role() -> None:
    """LE cliquet. Sur un corpus sain, rien de non-configuré — sans exception.

    Un échec ici ne dit pas « le code est cassé ». Il dit : *la source parle un mot que la
    table ne connaît pas*. La réponse n'est jamais de contourner le test — c'est de lire
    la balise, de décider de son rôle, et de l'écrire dans ``LEGI_ROLE_TABLE``.

    Depuis le cadrage « trois portes » (B-00-d), une balise non-configurée n'est plus un
    ``unknown`` dans la donnée : elle est ROUTÉE (metadata ou lien) et SIGNALÉE dans le
    ``ParseResult``. Le cliquet lit désormais le signal — il garde exactement la même
    chose : sur les fixtures saturées, il doit être vide.
    """
    orphelines: dict[str, set[str]] = {}

    for result in _parse_all():
        if result.unconfigured_tags:
            orphelines.setdefault("tag", set()).update(result.unconfigured_tags)
        if result.unknown_roots:
            orphelines.setdefault("racine", set()).update(result.unknown_roots)

    assert not orphelines, (
        f"Vocabulaire sans rôle dans LEGI_ROLE_TABLE : "
        f"{ {k: sorted(v) for k, v in orphelines.items()} }. "
        "Chaque balise doit porter un rôle — sinon sa donnée entre sans être comprise."
    )


def test_le_cliquet_est_CAPABLE_d_echouer() -> None:
    """Le contre-exemple, sans lequel le test précédent ne prouverait rien.

    Un test qui n'échoue jamais est un test qui n'observe rien. Celui-ci prouve que
    l'instrument fonctionne : sur la fixture qui porte une balise ``<ZORG>`` délibérément
    absente de la table, le ``ParseResult`` la **signale** — et sa valeur, routée par la
    cascade, entre en métadonnée sous sa clé chemin-complet au lieu de disparaître.
    """
    parser = GenericParser(LEGI_ROLE_TABLE, SourceName.LEGI)

    async def run():
        async for raw in LegiFileConnector(FIXTURES).fetch_all(OWNER):
            if any(Path(f).name == _FIXTURE_PATHOLOGIQUE for f in raw.payload["files"]):
                return parser.parse(raw)
        pytest.fail(f"La fixture {_FIXTURE_PATHOLOGIQUE} est introuvable")

    result = asyncio.run(run())

    assert "ZORG" in result.unconfigured_tags, (
        "La balise non-configurée doit être SIGNALÉE. Si elle ne l'est pas, le cliquet "
        "ci-dessus ne garde rien du tout."
    )
    assert result.document.metadata["article_zorg"], (
        "Et sa valeur doit être INGÉRÉE (porte metadata) — routée, pas jetée."
    )


def test_chaque_balise_porte_UN_role_et_un_seul() -> None:
    """La table est un dictionnaire : l'unicité est structurelle, pas conventionnelle.

    On ne peut pas mapper ``BLOC_TEXTUEL`` à la fois sur ``BODY`` et sur ``META`` — Python
    l'interdit. Ce test ne vérifie donc pas l'unicité (elle est acquise) mais que **chaque
    valeur est bien un ``Role``** : une chaîne s'y glisserait sans bruit et le
    ``role_of()`` du parser comparerait alors des pommes et des oranges.
    """
    for tag, role in LEGI_ROLE_TABLE.roles.items():
        assert isinstance(role, Role), f"{tag} porte {role!r}, qui n'est pas un Role"


def test_les_quatre_roles_sont_TOUS_utilises_par_LEGI() -> None:
    """LEGI exerce les quatre rôles — c'est ce qui en fait le cas d'épreuve du dispositif.

    La jurisprudence, elle, n'aura **aucune** balise ``VERSION`` : son handler ne
    s'activera pas, et c'est prévu (§3 : « version = stratégie optionnelle, no-op si
    absente »). Mais si LEGI n'exerçait pas les quatre, on n'aurait jamais éprouvé le
    routage complet avant d'y brancher cinq sources neuves.
    """
    exerces = set(LEGI_ROLE_TABLE.roles.values())
    assert exerces == set(Role), (
        f"Rôles jamais exercés par LEGI : {set(Role) - exerces}"
    )


def test_la_table_LEGI_ne_contient_AUCUNE_logique() -> None:
    """La mesure du succès de §3 : *une source nouvelle = une table, pas un parser*.

    ``sources/legi/`` ne doit plus contenir ni parser ni chunker. S'il en réapparaît un,
    c'est que la mécanique générique était incomplète — et c'est **elle** qu'il faut
    corriger, pas la source qu'il faut laisser diverger. C'est ainsi qu'on se retrouve
    avec six parsers.
    """
    modules = {
        p.name for p in (Path(__file__).parents[2] / "sources" / "legi").glob("*.py")
    }

    assert "parser.py" not in modules, (
        "Le parser est GÉNÉRIQUE : LEGI n'apporte qu'une table"
    )
    assert "chunking.py" not in modules, "Le chunker est GÉNÉRIQUE"
    assert {"table.py", "vocabulary.py", "file_connector.py"} <= modules
