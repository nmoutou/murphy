"""CLIQUET — la chaîne LEGI de bout en bout.

Ce test fait tourner ``connecteur → parser → extracteur → réduction → chunker`` sur les
fixtures et compare le résultat à un instantané versionné.

**Ce qu'il attrape et qu'aucun test unitaire n'attrape.** Chaque module peut passer ses
propres tests et la chaîne mentir quand même : un ``_invert`` qui revient double les
relations sans qu'aucun module ne s'en aperçoive ; une réduction qui déborde sur les
citations en efface sans qu'aucune assertion locale ne la voie ; un ``typelien`` qui
cesse d'être déclaré disparaît, tout simplement.

Ce cliquet fige le COMPORTEMENT de l'ensemble. Le faire bouger doit être un geste
délibéré — c'est sa seule raison d'être.
"""

import asyncio
import collections
from pathlib import Path

from ragcore.core.links import CANONICAL_VERBS, CONTAINS
from ragcore.core.models.enums import SourceName as _SN
from ragcore.core.models.identifiers import OwnerId
from ragcore.core.services.exclusion_reasons import (
    REASON_EXPORT_ARTIFACT,
    REASON_UNREADABLE,
)
from ragcore.core.services.relation_reduction import reduce_transitively
from ragcore.sources.generic import (
    GenericParser,
    GenericRelationExtractor,
    StructuralChunker,
)
from ragcore.sources.legi.file_connector import LegiFileConnector
from ragcore.sources.legi.table import LEGI_ROLE_TABLE
from ragcore.sources.legi.tests.conftest import (
    ARTICLE_HIERARCHISE,
    SECTION_GRAND_PARENTE,
    SECTION_PARENTE,
)

# Les fixtures vivent avec les tests de la source ; le cliquet les emprunte plutôt que de
# les dupliquer — deux jeux de fixtures dériveraient, et c'est le cliquet qui mentirait.
FIXTURES = Path(__file__).parents[2] / "sources" / "legi" / "tests" / "fixtures"

OWNER = OwnerId("u1")
CHUNK_SIZE = 128  # conf/base/parameters.yml
OVERLAP = 25


def _run() -> dict:
    """La chaîne complète, telle que le pipeline la fera tourner."""

    async def chain() -> dict:
        connector = LegiFileConnector(FIXTURES)
        parser = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        extractor = GenericRelationExtractor(LEGI_ROLE_TABLE, _SN.LEGI)
        chunker = StructuralChunker(max_chunk_size=CHUNK_SIZE, overlap=OVERLAP)

        documents = 0
        files = 0
        chunks = 0
        relations = []
        unknowns: dict[str, set[str]] = collections.defaultdict(set)

        async for raw in connector.fetch_all(OWNER):
            documents += 1
            files += len(raw.payload["files"])

            parsed = parser.parse(raw)
            extracted = extractor.extract(parsed)

            relations.extend(extracted.relations)
            chunks += len(chunker.chunk(parsed))

            for source in (parsed.unknowns, extracted.unknowns):
                for category, values in source.items():
                    unknowns[category].update(values)

        reduced = reduce_transitively(relations)

        return {
            "documents": documents,
            "files": files,
            "skipped": dict(connector.skipped),
            "before_reduction": len(relations),
            "after_reduction": len(reduced),
            "by_type": collections.Counter(r.relation_type for r in reduced),
            "unknowns": {k: sorted(v) for k, v in unknowns.items()},
            "chunks": chunks,
            "relations": relations,
            "reduced": reduced,
        }

    return asyncio.run(chain())


def test_la_chaine_complete_est_figee() -> None:
    """L'instantané. 10 fichiers, 9 documents — la paire ``TEXTE_VERSION``/``TEXTELR``
    n'en fait qu'un, et le ``versions.xml`` est écarté.

    **Le cliquet a bougé, sciemment : 122 → 123 arêtes.** L'arête de plus est
    ``zorglub`` — le ``typelien`` que la fixture déclare et que la table de LEGI ne sait
    pas traduire. L'ancien code le *déclarait* dans ``unknowns`` puis faisait
    ``return None`` : l'arête était perdue, et ce cliquet figeait sa perte. Le
    vocabulaire étant désormais ouvert, elle **entre dans le graphe sous son nom brut**.

    Un golden qui bouge d'exactement une arête, et qu'on sait nommer, est un golden qui a
    fait son travail.
    """
    result = _run()

    assert result["files"] == 10
    assert result["documents"] == 9
    # `malformed.xml` (illisible) était SILENCIEUSEMENT sauté : le connecteur le
    # `continue`-ait sans le compter, et ce golden était aveugle à sa disparition.
    # Depuis F3 il est écarté EN ÉTANT COMPTÉ (`unreadable`). Le golden bouge d'un
    # écart nommé — la fixture le contenait exprès, personne ne l'affirmait.
    assert result["skipped"] == {REASON_EXPORT_ARTIFACT: 1, REASON_UNREADABLE: 1}

    assert result["before_reduction"] == 123
    assert result["after_reduction"] == 116
    assert dict(result["by_type"]) == {
        "contains": 66,
        "cites": 41,
        "references": 4,
        "modifies": 2,
        "abrogates": 1,
        "creates": 1,
        # Le mot de LEGI, entré tel quel faute de traduction. Il n'est PAS canonique —
        # et c'est précisément ce que le graphe doit montrer.
        "zorglub": 1,
    }

    # **93 → 91 chunks, et c'est la normalisation typographique (§4) qui les fait tomber.**
    # Elle nettoie les espaces de bord de ligne (« texte. \n Suite » → « texte.\nSuite ») :
    # le texte est plus COURT du bruit d'encodage qu'il portait, donc il tient en deux
    # fenêtres de moins. Aucun contenu n'est perdu — c'est du blanc qui partait à
    # l'embedding et occupait des tokens pour rien.
    #
    # Cette bascule est exactement ce que `normalization.version: none -> v1` doit
    # signaler dans le hash (§6) : les vecteurs d'avant et d'après ne sont pas comparables,
    # et ils vivront donc dans deux collections Qdrant distinctes.
    assert result["chunks"] == 91


def test_un_typelien_inconnu_produit_une_ARETE_et_pas_un_vide() -> None:
    """LE test du lot, sur la chaîne complète.

    Le contrat a changé de camp. Avant : « l'inconnu est déclaré, et l'arête n'est pas
    écrite » — le fil rouge *nommait* le trou. Maintenant : « l'inconnu est déclaré, ET
    l'arête est écrite sous son nom brut » — il le *bouche*.

    Les deux moitiés comptent, et le test les vérifie ensemble : sans la déclaration, le
    mot inconnu entrerait en douce et personne n'apprendrait rien ; sans l'arête, on
    saurait ce qu'on a perdu, ce qui ne le rend pas moins perdu.
    """
    result = _run()

    raw_edges = [
        r for r in result["relations"] if r.relation_type not in CANONICAL_VERBS
    ]

    assert len(raw_edges) == 1, "l'unique typelien non traduit de la fixture"
    edge = raw_edges[0]

    assert edge.relation_type == "zorglub", (
        "le mot brut, normalisé, EST le type d'arête"
    )
    assert edge.metadata["typelien"] == "ZORGLUB", "et l'original survit en métadonnée"

    # …et il est déclaré. L'arête existe, l'aveu aussi.
    assert "ZORGLUB" in result["unknowns"]["typelien"]


def test_le_graphe_EXISTE() -> None:
    """La raison d'être du lot.

    L'ancien extracteur produisait **zéro relation** sur ce corpus : les 16 227 liens
    tombaient dans un ``except ValueError: continue``, parce qu'aucun des 16 ``typelien``
    réels ne correspondait à un membre de l'enum fermé. Le graphe entier s'évaporait sans
    une ligne de log.
    """
    result = _run()

    assert result["after_reduction"] > 0
    assert result["by_type"]["cites"] > 0  # la CITATION, 88 % du corpus réel


def test_la_reduction_nelimine_QUE_de_la_contenance() -> None:
    """Le garde-fou du §4, sur des données réelles.

    Réduire une citation détruirait un fait : « A cite B, B cite C, A cite C » est trois
    citations réelles. Ici on vérifie sur le corpus, pas sur un cas de laboratoire :
    toute arête que la réduction supprime est une contenance, et rien d'autre.
    """
    result = _run()

    eliminated = [r for r in result["relations"] if r not in result["reduced"]]

    assert eliminated, "la fixture hiérarchisée doit produire des arêtes redondantes"
    for relation in eliminated:
        assert relation.relation_type == CONTAINS


def test_la_fermeture_des_ancetres_est_ramenee_a_larbre() -> None:
    """Le cas mesuré, dans les deux sens.

    ``<CONTEXTE>`` déclare la fermeture : la grand-parente ET la parente contiennent
    l'article. ``<STRUCTURE_TA>`` déclare l'arbre : grand-parente ⊃ parente ⊃ article.
    L'arête directe « grand-parente ⊃ article » est donc redondante avec le chemin — elle
    doit tomber, et le chemin doit rester.
    """
    result = _run()

    edges = {
        (r.source_identifier.raw, r.target_identifier.raw)
        for r in result["reduced"]
        if r.relation_type == CONTAINS
    }

    # Le chemin survit…
    assert (SECTION_GRAND_PARENTE, SECTION_PARENTE) in edges
    assert (SECTION_PARENTE, ARTICLE_HIERARCHISE) in edges
    # …et le raccourci redondant tombe.
    assert (SECTION_GRAND_PARENTE, ARTICLE_HIERARCHISE) not in edges


def test_les_citations_traversent_la_reduction_INTACTES() -> None:
    """Sur le corpus complet, la réduction fait passer ``contains`` de 7621 à 4100 et ne
    touche PAS aux 14 286 citations. Ici, à l'échelle des fixtures : leur nombre est le
    même avant et après.
    """
    result = _run()

    before = collections.Counter(r.relation_type for r in result["relations"])["cites"]

    assert result["by_type"]["cites"] == before


def test_les_inconnus_sont_DECLARES_et_pas_jetes() -> None:
    """Le tuyau ``unknowns`` a enfin un producteur — et il en a trois.

    Le corpus RÉEL n'en déclare aucun : les 16 ``typelien`` sont couverts, et le
    vocabulaire est saturé. C'est le résultat attendu, et c'est exactement pourquoi il ne
    peut pas prouver l'instrument : un test qui n'observe jamais d'inconnu ne démontre pas
    qu'on saurait en déclarer un. D'où la fixture synthétique.
    """
    result = _run()

    assert result["unknowns"] == {
        "typelien": ["ZORGLUB"],
        "sens": ["lateral"],
        "balise": ["ZORG"],
    }
