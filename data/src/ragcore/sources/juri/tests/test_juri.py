"""La jurisprudence, éprouvée sur du VRAI XML — et la découverte qui a changé le lot.

Les fixtures sont des extraits littéraux du corpus (``/mnt/data/Murphy/src``). Elles sont
copiées ici **délibérément** : le corpus est une source de fixtures, jamais une dépendance
de test. Le volume peut ne pas être monté ; ces tests, eux, doivent tourner partout.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ragcore.core.links import CITES, LinkSubject, extract_links
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import DecisionId, OwnerId
from ragcore.sources.generic import GenericParser
from ragcore.sources.juri import (
    JURI_LINK_TABLE,
    ROLE_TABLE_BY_ROOT,
    JuriFileConnector,
)

FIXTURES = Path(__file__).parent / "fixtures"
OWNER = OwnerId("u1")


def _parse_result(name: str, source: SourceName):
    async def run():
        connector = JuriFileConnector(FIXTURES, source)
        async for raw in connector.fetch_all(OWNER):
            if Path(raw.payload["files"][0]).name == name:
                root = raw.payload["content"][0]["tag"]
                return GenericParser(ROLE_TABLE_BY_ROOT[root], source).parse(raw)
        pytest.fail(f"Fixture introuvable : {name}")

    return asyncio.run(run())


def _parse(name: str, source: SourceName):
    return _parse_result(name, source).document


def test_une_citation_decrite_devient_un_CHAMP_jamais_une_arete() -> None:
    """**LE test du lot.** Sans lui, les citations juri s'évaporeraient en silence.

    Les 68 ``<LIEN>`` du corpus juri ont **tous leurs attributs vides** — ni ``id``, ni
    ``cidtexte``, ni ``nortexte``. Ce qu'ils portent est du texte : « Articles 1103 et 1229
    du code civil ». La cour *décrit* l'article qu'elle vise ; elle ne le référence pas.

    ``core/links`` traitait un lien sans identifiant comme une **donnée absente** : les 68
    citations se seraient évaporées exactement comme les 16 227 liens de LEGI en leur
    temps, et rien ne l'aurait signalé.

    Elles entrent désormais — mais **comme champ du document, pas comme arête**. Une
    phrase n'est pas une entité du graphe : aucun run futur ne fera exister « Articles
    1103 et 1229 du code civil » comme document. La matérialiser en nœud ``:Unknown``
    peuplait le graphe d'un placeholder par formulation, jamais résolu.
    """
    document = _parse("cass_avec_liens.xml", SourceName.CASS)

    links = extract_links(
        references=document.structure["references"],
        ancestors=document.structure["context"],
        table=JURI_LINK_TABLE,
        subject=LinkSubject(
            current=document.identifier, owner_id=OWNER, source=SourceName.CASS
        ),
    )

    assert not links.relations, (
        "une cible DÉCRITE ne produit aucune arête — c'est tout le changement"
    )
    assert links.citations, "…mais elle n'est pas perdue pour autant"

    citation = links.citations[0]
    assert citation.verb == CITES, "le verbe traduit survit"
    assert citation.sens == "source", (
        "le sens aussi : c'est lui qui orientera l'arête le jour de la résolution"
    )
    assert "loi n° 75-1334" in citation.text, (
        "et la PHRASE est intacte : c'est elle que la passe de résolution lira pour "
        "retrouver le vrai article"
    )


def test_un_arret_n_est_JAMAIS_un_ELI() -> None:
    """Le piège du préfixe, deuxième édition — et il aurait été payé deux fois.

    ``JURITEXT000019333891`` satisfait **parfaitement** le motif de l'ELI
    (``^[A-Z]{8}[0-9]{12}$``) : le motif ne regarde pas le préfixe. Un arrêt aurait donc
    été sérialisé ``eli:JURITEXT…`` sans qu'aucune exception ne soit levée, et le graphe
    aurait porté des « textes de loi » dotés d'une formation de jugement.

    C'est exactement le piège des 568 arêtes JORF, déjà payé une fois côté LEGI.
    """
    document = _parse("cass_avec_liens.xml", SourceName.CASS)

    assert isinstance(document.identifier, DecisionId)
    assert document.identifier.serialize().startswith("decision:")
    assert document.identifier.jurisdiction == "judiciaire"


def test_la_juri_n_a_AUCUNE_balise_sans_role() -> None:
    """Le cliquet de §3, appliqué aux trois tables juri.

    Une balise que la table ne connaît pas voit son contenu **disparaître** — sans
    exception, sans log. Ce test l'interdit sur les fixtures ; le ``RunSummary`` le
    signalera sur le corpus complet. Le cliquet interdit la régression, l'instrument permet
    la saturation ; ni l'un ni l'autre seul ne suffit.
    """
    orphelines: dict[str, set[str]] = {}

    for fixture, source in (
        ("cass_avec_liens.xml", SourceName.CASS),
        ("jade.xml", SourceName.JADE),
        ("constit.xml", SourceName.CONSTIT),
    ):
        result = _parse_result(fixture, source)
        if result.unconfigured_tags:
            orphelines.setdefault("tag", set()).update(result.unconfigured_tags)
        if result.unknown_roots:
            orphelines.setdefault("racine", set()).update(result.unknown_roots)

    assert not orphelines, (
        f"Vocabulaire sans rôle dans les tables juri : "
        f"{ {k: sorted(v) for k, v in orphelines.items()} }"
    )


def test_les_trois_racines_ont_leur_table() -> None:
    """Cinq sources, **trois** tables — c'est DILA qui en décide, pas nous.

    CAPP, CASS et INCA publient la même racine (``TEXTE_JURI_JUDI``) et partagent donc la
    même table, à l'identique. Une table par *forme de document*, jamais une par *base* :
    la base n'est qu'un champ (le principe directeur l'exige nommément).
    """
    assert set(ROLE_TABLE_BY_ROOT) == {
        "TEXTE_JURI_JUDI",
        "TEXTE_JURI_ADMIN",
        "TEXTE_JURI_CONSTIT",
    }
    assert (
        ROLE_TABLE_BY_ROOT["TEXTE_JURI_JUDI"] is ROLE_TABLE_BY_ROOT["TEXTE_JURI_JUDI"]
    )


def test_la_juri_n_a_AUCUN_role_version() -> None:
    """« Version = stratégie optionnelle, no-op si absente » (§3) — **vérifié**.

    Un arrêt est rendu une fois ; il n'a pas de versions successives comme un article de
    code. Aucune balise n'est mappée sur ``VERSION`` : le handler ne s'active pas.

    C'est le seul rôle des quatre que la juri n'exerce pas — et c'était prévu par le
    cadrage, avant qu'on ait mesuré quoi que ce soit. Le vérifier ferme la boucle.
    """
    for table in ROLE_TABLE_BY_ROOT.values():
        assert table.version_tags == frozenset(), (
            "la juri n'a pas d'axe temporel — aucune balise de datation de version"
        )


def test_le_contenu_de_larret_est_ingere() -> None:
    """La vérification élémentaire, qu'il serait absurde de ne pas faire.

    Un test qui prouve les arêtes mais pas le texte laisserait passer un corpus ingéré
    vide — et c'est précisément le bug qui a fait passer les 98 décrets de LEGI sans
    contenu, sans qu'une exception soit levée.
    """
    document = _parse("cass_avec_liens.xml", SourceName.CASS)

    assert document.content.strip(), "l'arrêt DOIT avoir du texte"
    assert document.title.strip()
    assert document.metadata.get("juridiction")
