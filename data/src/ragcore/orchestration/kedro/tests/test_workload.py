"""Le workload : il déclare les inconnus d'extraction, et la phase 1 n'écrit aucune
arête.

Le second point se prouve contre un vrai ``IngestDocumentUseCase`` sur un graphe en
mémoire : le nœud est écrit, ``graph.edges`` reste vide. Les relations non formatées,
elles, sont écrites dès la phase 1 (ADR-045).
"""

from __future__ import annotations

from ragcore.application.ingest_document import (
    IngestDocumentUseCase,
    IngestionStores,
)
from ragcore.application.run_context import PipelineContext
from ragcore.core.links import CITE
from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.relation import Relation
from ragcore.core.models.unformatted_relation import UnformattedRelation
from ragcore.core.models.unknown_tally import UnknownExample, UnknownTally
from ragcore.core.ports.relation_extractor import ExtractionResult
from ragcore.core.services.unknown_categories import CATEGORY_LINK
from ragcore.core.telemetry_events import PAYLOAD_COUNT_KEY, RELATION_UNKNOWN
from ragcore.orchestration.kedro.workload import WorkloadSteps, build_document_workload
from ragcore.tests.fakes import (
    FakeRuntime,
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryPendingRepository,
    InMemoryUnformattedRepository,
    InMemoryVectorRepository,
    RecordingTelemetry,
)

SELF = Identifier(raw="LEGIARTI000000000001")
OTHER = Identifier(raw="LEGIARTI000000000002")
SOURCE_FILE = "LEGIARTI000000000001.xml"
DESCRIBED = UnformattedRelation(
    source_identifier=SELF,
    target_text="code de l'environnement",
    relation_type=CITE,
    sens="source",
    source=SourceName.LEGI,
)


def _doc() -> ParsedDocument:
    return ParsedDocument(
        identifier=SELF,
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title="Article",
        content="Le contenu réel de l'article, en français.",
        structure={},
        metadata={},
        source_files=(SOURCE_FILE,),
    )


def _zorglub_seen_once() -> dict[str, dict[str, UnknownTally]]:
    example = UnknownExample(identifier=SELF.serialize(), source_file=SOURCE_FILE)
    return {CATEGORY_LINK: {"ZORGLUB": UnknownTally(count=1, example=example)}}


class _StubChunker:
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        return [
            Chunk(
                chunk_id=f"{document.identifier.raw}_0000",
                parent_identifier=document.identifier,
                document_type=DocumentType.ARTICLE,
                ordinal=0,
                text=document.content,
                tag_path=[],
                char_start=0,
                char_end=len(document.content),
                metadata={},
            )
        ]


class _StubEmbedder:
    dimension = 3

    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=[0.0] * 3,
                embedding_model="stub",
                embedding_dim=3,
            )
            for chunk in chunks
        ]


class _StubExtractor:
    """Un résultat fixe : une relation, une relation non formatée, un inconnu, et à la
    demande des liens perdus."""

    def __init__(self, lost_links: int = 0) -> None:
        self.calls = 0
        self._lost_links = lost_links

    def extract(self, document: ParsedDocument) -> ExtractionResult:
        self.calls += 1
        return ExtractionResult(
            relations=[
                Relation(
                    source_identifier=SELF,
                    target_identifier=OTHER,
                    relation_type=CITE,
                    source=SourceName.LEGI,
                )
            ],
            unformatted_relations=[DESCRIBED],
            unknowns={CATEGORY_LINK: ["ZORGLUB"]},
            lost_links=self._lost_links,
        )


def _use_case_factory(
    graph: InMemoryGraphRepository,
    vectors: InMemoryVectorRepository,
    unformatted: InMemoryUnformattedRepository,
):
    """Les dépôts en mémoire sont partagés : le test ne parallélise pas."""

    def factory(telemetry) -> IngestDocumentUseCase:  # noqa: ANN001
        return IngestDocumentUseCase(
            IngestionStores(
                documents=InMemoryDocumentRepository(),
                graph=graph,
                vectors=vectors,
                pending=InMemoryPendingRepository(),
                unformatted=unformatted,
            ),
            telemetry,
        )

    return factory


def _run(
    document: ParsedDocument,
    extractor: _StubExtractor | None = None,
    embedding_enabled: bool = True,
    unformatted: InMemoryUnformattedRepository | None = None,
):
    graph = InMemoryGraphRepository()
    vectors = InMemoryVectorRepository()
    context = PipelineContext.create(sources=(SourceName.LEGI,))
    workload = build_document_workload(
        steps=WorkloadSteps(
            chunker=_StubChunker(),
            embedder=_StubEmbedder(),
            extractor=extractor or _StubExtractor(),
        ),
        use_case_factory=_use_case_factory(
            graph, vectors, unformatted or InMemoryUnformattedRepository()
        ),
        context=context,
        embedding_enabled=embedding_enabled,
    )
    runtime = FakeRuntime(worker_id=0)
    telemetry = RecordingTelemetry()
    try:
        result = workload(document, runtime, telemetry)
    finally:
        runtime.close()
    return result, graph, vectors, telemetry


def test_les_inconnus_de_lextraction_sont_DECLARES() -> None:
    """Les inconnus d'extraction rejoignent l'agrégat du worker ; ceux du parse sont
    déclarés ailleurs."""
    _result, _graph, _vectors, telemetry = _run(_doc())

    unknowns = telemetry.snapshot().unknowns
    assert unknowns == _zorglub_seen_once()


def test_les_liens_perdus_sont_COMPTES_en_relation_unknown() -> None:
    """Les liens perdus sont comptés en ``relation.unknown`` (ADR-048)."""
    _result, _graph, _vectors, telemetry = _run(
        _doc(), extractor=_StubExtractor(lost_links=2)
    )

    (event,) = telemetry.events_of(RELATION_UNKNOWN)
    assert event.payload == {PAYLOAD_COUNT_KEY: 2}


def test_sans_lien_perdu_relation_unknown_n_est_PAS_emis() -> None:
    _result, _graph, _vectors, telemetry = _run(_doc())

    assert telemetry.events_of(RELATION_UNKNOWN) == []


def test_la_phase_1_NECRIT_AUCUNE_arete() -> None:
    """Le nœud est écrit, pas l'arête : sa cible n'est peut-être pas encore un nœud."""
    result, graph, _vectors, _telemetry = _run(_doc())

    assert graph.nodes == {SELF.serialize()}  # le nœud est écrit…
    assert graph.edges == []  # …mais aucune arête
    # La relation ressort intacte pour la phase 2
    assert len(result.relations) == 1
    assert result.relations[0].relation_type == CITE


def test_les_relations_non_formatees_sont_ECRITES_des_la_phase_1() -> None:
    """ADR-045 : une cible décrite n'attend aucun nœud, la saga l'écrit."""
    unformatted = InMemoryUnformattedRepository()

    _run(_doc(), unformatted=unformatted)

    assert [row.relation for row in unformatted.rows.values()] == [DESCRIBED]


def test_extract_est_appele_une_seule_fois_par_document() -> None:
    """Le seul appelant d'``extract()``, une fois par document."""
    extractor = _StubExtractor()

    _run(_doc(), extractor=extractor)

    assert extractor.calls == 1


def test_aucun_inconnu_fantome_cote_parse() -> None:
    """Aucun inconnu fantôme côté parse : le workload ne déclare que ceux de
    l'extraction."""
    _result, _graph, _vectors, telemetry = _run(_doc())

    assert telemetry.snapshot().unknowns == _zorglub_seen_once()


def test_embedding_actif_ecrit_les_vecteurs() -> None:
    """Témoin du test suivant : le chemin nominal écrit bien un vecteur."""
    _result, _graph, vectors, _telemetry = _run(_doc(), embedding_enabled=True)

    assert len(vectors.chunks) == 1  # le chunk unique du stub, embarqué et upserté


def test_embedding_coupe_nECRIT_AUCUN_vecteur_mais_merge_le_noeud() -> None:
    """ADR-023 : ``embedding_enabled=False`` n'écrit aucun vecteur, mais le nœud et la
    relation suivent leur cours."""
    result, graph, vectors, _telemetry = _run(_doc(), embedding_enabled=False)

    assert vectors.chunks == []  # rien d'embarqué, rien d'upserté
    assert graph.nodes == {SELF.serialize()}  # …mais le nœud est bien écrit
    assert len(result.relations) == 1  # …et la relation part en phase 2, intacte
