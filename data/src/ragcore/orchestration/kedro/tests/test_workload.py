"""Le workload : il déclare les inconnus d'extraction, et la phase 1 n'écrit aucune
arête.

Le second point se prouve contre un vrai ``IngestDocumentUseCase`` sur un graphe en
mémoire : le nœud est écrit, ``graph.edges`` reste vide. Les relations non formatées,
elles, sont écrites dès la phase 1 (ADR-021).
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
    InMemorySearchIndex,
    InMemoryUnformattedRepository,
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


TITLE_VECTOR = [1.0, 1.0, 1.0]


def _doc(
    content: str = "Le contenu réel de l'article, en français.", title: str = "Article"
) -> ParsedDocument:
    return ParsedDocument(
        identifier=SELF,
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title=title,
        content=content,
        structure={},
        metadata={},
        source_files=(SOURCE_FILE,),
    )


def _zorglub_seen_once() -> dict[str, dict[str, UnknownTally]]:
    example = UnknownExample(identifier=SELF.serialize(), source_file=SOURCE_FILE)
    return {CATEGORY_LINK: {"ZORGLUB": UnknownTally(count=1, example=example)}}


class _StubChunker:
    """Un chunk par document, aucun sans contenu."""

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        if not document.content:
            return []
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

    async def embed_text(self, text: str) -> list[float]:
        return list(TITLE_VECTOR)


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
    search_index: InMemorySearchIndex,
    unformatted: InMemoryUnformattedRepository,
):
    """Les dépôts en mémoire sont partagés : le test ne parallélise pas."""

    def factory(telemetry, runtime) -> IngestDocumentUseCase:  # noqa: ANN001
        return IngestDocumentUseCase(
            IngestionStores(
                documents=InMemoryDocumentRepository(),
                graph=graph,
                search_index=search_index,
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
    search_index = InMemorySearchIndex()
    context = PipelineContext.create(sources=(SourceName.LEGI,))
    workload = build_document_workload(
        steps=WorkloadSteps(
            chunker=_StubChunker(),
            embedder=_StubEmbedder(),
            extractor=extractor or _StubExtractor(),
        ),
        use_case_factory=_use_case_factory(
            graph, search_index, unformatted or InMemoryUnformattedRepository()
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
    return result, graph, search_index, telemetry


def test_les_inconnus_de_lextraction_sont_DECLARES() -> None:
    """Les inconnus d'extraction rejoignent l'agrégat du worker ; ceux du parse sont
    déclarés ailleurs."""
    _result, _graph, _search_index, telemetry = _run(_doc())

    unknowns = telemetry.snapshot().unknowns
    assert unknowns == _zorglub_seen_once()


def test_les_liens_perdus_sont_COMPTES_en_relation_unknown() -> None:
    """Les liens perdus sont comptés en ``relation.unknown`` (ADR-024)."""
    _result, _graph, _search_index, telemetry = _run(
        _doc(), extractor=_StubExtractor(lost_links=2)
    )

    (event,) = telemetry.events_of(RELATION_UNKNOWN)
    assert event.payload == {PAYLOAD_COUNT_KEY: 2}


def test_sans_lien_perdu_relation_unknown_n_est_PAS_emis() -> None:
    _result, _graph, _search_index, telemetry = _run(_doc())

    assert telemetry.events_of(RELATION_UNKNOWN) == []


def test_la_phase_1_NECRIT_AUCUNE_arete() -> None:
    """Le nœud est écrit, pas l'arête : sa cible n'est peut-être pas encore un nœud."""
    result, graph, _search_index, _telemetry = _run(_doc())

    assert graph.nodes == {SELF.serialize()}  # le nœud est écrit…
    assert graph.edges == []  # …mais aucune arête
    # La relation ressort intacte pour la phase 2
    assert len(result.relations) == 1
    assert result.relations[0].relation_type == CITE


def test_les_relations_non_formatees_sont_ECRITES_des_la_phase_1() -> None:
    """ADR-021 : une cible décrite n'attend aucun nœud, la saga l'écrit."""
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
    _result, _graph, _search_index, telemetry = _run(_doc())

    assert telemetry.snapshot().unknowns == _zorglub_seen_once()


def test_embedding_actif_ecrit_les_vecteurs_des_passages_SANS_celui_du_titre() -> None:
    """ADR-029 : le titre d'un document qui a des passages n'est pas embarqué."""
    _result, _graph, search_index, _telemetry = _run(_doc(), embedding_enabled=True)

    content = search_index.documents[SELF.serialize()]
    (passage,) = content.passages
    assert passage.embedding == [0.0] * 3
    assert content.title_embedding is None


def test_un_document_sans_passage_recoit_le_VECTEUR_DE_SON_TITRE() -> None:
    """ADR-029 : sans lui, une section n'est trouvée que par la recherche lexicale."""
    _result, _graph, search_index, _telemetry = _run(_doc(content=""))

    content = search_index.documents[SELF.serialize()]
    assert content.passages == ()
    assert content.title_embedding == TITLE_VECTOR


def test_un_document_sans_passage_ni_titre_na_AUCUN_vecteur() -> None:
    _result, _graph, search_index, _telemetry = _run(_doc(content="", title=""))

    assert search_index.documents[SELF.serialize()].title_embedding is None


def test_embedding_coupe_ecrit_les_passages_SANS_VECTEUR_et_merge_le_noeud() -> None:
    """ADR-012 : ``embedding_enabled=False`` n'écrit aucun vecteur, mais les passages
    restent cherchables par leur texte, et le nœud et la relation suivent leur cours."""
    result, graph, search_index, _telemetry = _run(_doc(), embedding_enabled=False)

    content = search_index.documents[SELF.serialize()]
    (passage,) = content.passages
    assert passage.embedding is None
    assert content.title_embedding is None
    assert graph.nodes == {SELF.serialize()}  # …mais le nœud est bien écrit
    assert len(result.relations) == 1  # …et la relation part en phase 2, intacte


def test_embedding_coupe_nembarque_pas_le_titre_dun_document_sans_passage() -> None:
    _result, _graph, search_index, _telemetry = _run(
        _doc(content=""), embedding_enabled=False
    )

    assert search_index.documents[SELF.serialize()].title_embedding is None
