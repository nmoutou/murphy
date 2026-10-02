"""Cliquet : la chaîne LEGI de bout en bout, comparée à un instantané versionné.

Il attrape ce qu'aucun test unitaire ne voit : des relations doublées, une réduction qui
déborde sur les citations, un ``typelien`` qui disparaît. Le faire bouger doit être un
geste délibéré.
"""

import asyncio
import collections
from pathlib import Path

from ragcore.core.links import CANONICAL_VERBS, CONTIENT
from ragcore.core.models.enums import SourceName as _SN
from ragcore.core.models.processing import ChunkingConfig
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
from ragcore.sources.legislatif.file_connector import LegiFileConnector
from ragcore.sources.legislatif.table import LEGI_ROLE_TABLE
from ragcore.sources.legislatif.tests.conftest import (
    ARTICLE_HIERARCHISE,
    SECTION_GRAND_PARENTE,
    SECTION_PARENTE,
)

# Les fixtures de la source, empruntées : deux jeux dériveraient
FIXTURES = Path(__file__).parents[2] / "sources" / "legislatif" / "tests" / "fixtures"

CHUNK_SIZE = 128
OVERLAP = 25


def _run() -> dict:
    async def chain() -> dict:
        connector = LegiFileConnector(FIXTURES)
        parser = GenericParser(LEGI_ROLE_TABLE, _SN.LEGI)
        extractor = GenericRelationExtractor(LEGI_ROLE_TABLE, _SN.LEGI)
        chunker = StructuralChunker(
            ChunkingConfig(max_chars=CHUNK_SIZE, overlap_chars=OVERLAP)
        )

        documents = 0
        files = 0
        chunks = 0
        relations = []
        unknowns: dict[str, set[str]] = collections.defaultdict(set)

        async for raw in connector.fetch_all():
            documents += 1
            files += len(raw.payload["files"])

            result = parser.parse(raw)
            parsed = result.document
            extracted = extractor.extract(parsed)

            relations.extend(extracted.relations)
            chunks += len(chunker.chunk(parsed))

            # Côté parse, la donnée non configurée est routée et signalée : le cliquet
            # agrège le signal sous les catégories du bilan.
            signals = {
                "tags": result.unconfigured_tags,
                "links": result.unconfigured_links,
                "roots": result.unknown_roots,
            }
            for category, values in signals.items():
                if values:
                    unknowns[category].update(values)
            for category, values in extracted.unknowns.items():
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
    """10 fichiers, 9 documents : la paire ``TEXTE_VERSION``/``TEXTELR`` n'en fait
    qu'un, et le ``versions.xml`` est écarté."""
    result = _run()

    assert result["files"] == 10
    assert result["documents"] == 9
    # `malformed.xml` est écarté et compté (`unreadable`)
    assert result["skipped"] == {REASON_EXPORT_ARTIFACT: 1, REASON_UNREADABLE: 1}

    # L'axe temporel est une chaîne `suivi_par` : chaque document n'émet que les
    # maillons qui le touchent (2 + 1 + 0 = 3).
    assert result["before_reduction"] == 126
    assert result["after_reduction"] == 119  # 116 + 3 : la réduction n'y touche pas
    assert dict(result["by_type"]) == {
        "contient": 66,
        "cite": 41,
        "suivi_par": 3,  # l'axe temporel : une CHAÎNE, plus un produit cartésien
        "modifie": 2,
        "concorde": 2,
        "abroge": 1,
        "cree": 1,
        "codifie": 1,
        "applique": 1,
        # Le mot de LEGI, entré tel quel faute de traduction : non canonique
        "zorglub": 1,
    }

    # La normalisation typographique raccourcit le texte : moins de fenêtres.
    assert result["chunks"] == 91


def test_un_typelien_inconnu_produit_une_ARETE_et_pas_un_vide() -> None:
    """L'inconnu est déclaré, et l'arête est quand même écrite sous son nom brut."""
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

    # …et il est déclaré
    assert "ZORGLUB" in result["unknowns"]["links"]


def test_le_graphe_EXISTE() -> None:
    """Aucun ``typelien`` réel ne doit faire perdre de relation."""
    result = _run()

    assert result["after_reduction"] > 0
    assert result["by_type"]["cite"] > 0  # la CITATION, 88 % du corpus réel


def test_la_reduction_nelimine_QUE_de_la_contenance() -> None:
    """Sur des données réelles, toute arête supprimée par la réduction est une
    contenance : réduire une citation détruirait un fait."""
    result = _run()

    eliminated = [r for r in result["relations"] if r not in result["reduced"]]

    assert eliminated, "la fixture hiérarchisée doit produire des arêtes redondantes"
    for relation in eliminated:
        assert relation.relation_type == CONTIENT


def test_la_fermeture_des_ancetres_est_ramenee_a_larbre() -> None:
    """``<CONTEXTE>`` déclare la fermeture, ``<STRUCTURE_TA>`` l'arbre : le raccourci
    « grand-parente ⊃ article » tombe, le chemin reste."""
    result = _run()

    edges = {
        (r.source_identifier.raw, r.target_identifier.raw)
        for r in result["reduced"]
        if r.relation_type == CONTIENT
    }

    # Le chemin survit…
    assert (SECTION_GRAND_PARENTE, SECTION_PARENTE) in edges
    assert (SECTION_PARENTE, ARTICLE_HIERARCHISE) in edges
    # …et le raccourci redondant tombe.
    assert (SECTION_GRAND_PARENTE, ARTICLE_HIERARCHISE) not in edges


def test_les_citations_traversent_la_reduction_INTACTES() -> None:
    """La réduction ne touche pas aux citations : leur nombre est le même avant et
    après."""
    result = _run()

    before = collections.Counter(r.relation_type for r in result["relations"])["cite"]

    assert result["by_type"]["cite"] == before


def test_les_inconnus_sont_DECLARES_et_pas_jetes() -> None:
    """Le corpus réel ne déclare aucun inconnu : la fixture synthétique prouve que
    l'instrument saurait en déclarer."""
    result = _run()

    # Trois catégories plates (ADR-024). Les balises connues sans renommage sont non
    # configurées aussi (ADR-023). `sens="lateral"` n'est pas un type de lien : c'est un
    # lien perdu, compté en `relation.unknown`.
    assert result["unknowns"] == {
        "links": ["ZORGLUB"],
        "tags": [
            "article_zorg",
            "article_zorg_attribut_inconnu",
        ],
    }
