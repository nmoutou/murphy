"""Le workload — le dernier maillon d'``unknowns``, et la frontière phase-1/phase-2.

Deux propriétés se prouvent ici, et aucune autre ne comptait autant dans les lots
3-4 :

1. **Un inconnu remonté dans la donnée est DÉCLARÉ.** Le parser et l'extracteur ne
   voient jamais la télémétrie ; ils remontent leurs inconnus dans ``parsed.unknowns``
   et ``extraction.unknowns``. Le workload, qui tient la ``WorkerTelemetry`` du worker,
   les déclare. Sans cet appel, ``RunStats.unknowns`` resterait le tuyau vide qu'il
   était — plombé de bout en bout, sans producteur.

2. **La phase 1 n'écrit AUCUNE arête.** Le workload extrait les relations et les
   remonte dans ``WorkloadResult`` ; il ne les passe pas au graphe. On le prouve
   contre un vrai ``IngestDocumentUseCase`` posé sur un vrai graphe en mémoire : le
   nœud est mergé, mais ``graph.edges`` reste vide.
"""

from __future__ import annotations

from ragcore.application.ingest_document import (
    IngestDocumentUseCase,
    IngestionStores,
)
from ragcore.application.run_context import PipelineContext
from ragcore.core.links import CITES
from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import Operation, SourceName
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.relation import Relation
from ragcore.core.ports.relation_extractor import ExtractionResult
from ragcore.orchestration.kedro.workload import WorkloadSteps, build_document_workload
from ragcore.tests.fakes import (
    FakeRuntime,
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryManifestRepository,
    InMemoryVectorRepository,
    RecordingTelemetry,
)

SELF = Identifier(raw="LEGIARTI000000000001")
OTHER = Identifier(raw="LEGIARTI000000000002")


def _doc() -> ParsedDocument:
    return ParsedDocument(
        identifier=SELF,
        source=SourceName.LEGI,
        title="Article",
        content="Le contenu réel de l'article, en français.",
        structure={},
        metadata={},
    )


class _StubChunker:
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        return [
            Chunk(
                chunk_id=f"{document.identifier.raw}_0000",
                parent_identifier=document.identifier,
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
    """Rend un résultat FIXE — le workload n'invente rien, il transmet.

    Une relation (pour prouver qu'elle sort sans être écrite) et un inconnu (pour
    prouver qu'il est déclaré).
    """

    def __init__(self) -> None:
        self.calls = 0

    def extract(self, document: ParsedDocument) -> ExtractionResult:
        self.calls += 1
        return ExtractionResult(
            relations=[
                Relation(
                    source_identifier=SELF,
                    target_identifier=OTHER,
                    relation_type=CITES,
                    source=SourceName.LEGI,
                )
            ],
            unknowns={"typelien": ["ZORGLUB"]},
        )


def _use_case_factory(
    graph: InMemoryGraphRepository, vectors: InMemoryVectorRepository
):
    """Fabrique un use case sur le graphe et le dépôt de vecteurs donnés — la télémétrie
    du worker est celle que le workload passe. On construit les dépôts en mémoire une
    fois et on les partage : le test ne parallélise pas, la contrainte de boucle ne s'y
    applique pas.
    """

    def factory(telemetry) -> IngestDocumentUseCase:  # noqa: ANN001
        return IngestDocumentUseCase(
            IngestionStores(
                documents=InMemoryDocumentRepository(),
                manifest=InMemoryManifestRepository(),
                graph=graph,
                vectors=vectors,
            ),
            telemetry,
        )

    return factory


def _run(
    document: ParsedDocument,
    extractor: _StubExtractor | None = None,
    embedding_enabled: bool = True,
):
    graph = InMemoryGraphRepository()
    vectors = InMemoryVectorRepository()
    context = PipelineContext.create(source=SourceName.LEGI)
    workload = build_document_workload(
        steps=WorkloadSteps(
            chunker=_StubChunker(),
            embedder=_StubEmbedder(),
            extractor=extractor or _StubExtractor(),
        ),
        use_case_factory=_use_case_factory(graph, vectors),
        context=context,
        embedding_enabled=embedding_enabled,
    )
    runtime = FakeRuntime(worker_id=0)
    telemetry = RecordingTelemetry()
    try:
        result = workload(document, Operation.INSERT, runtime, telemetry)
    finally:
        runtime.close()
    return result, graph, vectors, telemetry


def test_les_inconnus_de_lextraction_sont_DECLARES() -> None:
    """Les inconnus d'EXTRACTION rejoignent l'agrégat du worker.

    ``extraction.unknowns`` vient de l'extracteur, qui ne tient pas la télémétrie.
    C'est le workload qui les déclare — et ``snapshot()`` est la preuve que le tuyau
    coule. Les inconnus de PARSE n'existent plus : les balises
    non-configurées sont routées par la cascade et signalées au site de parse
    (``computeIdempotence``, ``tag.unconfigured``), jamais ici.
    """
    _result, _graph, _vectors, telemetry = _run(_doc())

    unknowns = telemetry.snapshot().unknowns
    assert unknowns == {"typelien": ["ZORGLUB"]}


def test_la_phase_1_NECRIT_AUCUNE_arete() -> None:
    """Le nœud est mergé, l'arête ne l'est pas : elle attend la phase 2 (§11).

    Écrire l'arête ici la ferait dépendre de l'ordre d'ingestion : sa cible peut ne
    pas encore être un nœud. On le prouve contre un vrai use case sur un vrai graphe
    en mémoire — pas contre un espion complaisant.
    """
    result, graph, _vectors, _telemetry = _run(_doc())

    assert graph.nodes == {SELF.serialize()}  # le nœud est écrit…
    assert graph.edges == []  # …mais aucune arête
    # La relation ressort pour la phase 2, intacte.
    assert len(result.relations) == 1
    assert result.relations[0].relation_type == CITES


def test_extract_est_appele_une_seule_fois_par_document() -> None:
    """Le workload est le SEUL appelant de ``extract()`` — et il l'appelle une fois."""
    extractor = _StubExtractor()

    _run(_doc(), extractor=extractor)

    assert extractor.calls == 1


def test_aucun_inconnu_fantome_cote_parse() -> None:
    """L'extracteur stub déclare toujours ``ZORGLUB`` ; ce qu'on vérifie ici, c'est
    qu'aucun inconnu FANTÔME n'apparaît côté parse — le workload n'a plus rien à
    déclarer pour le parsing, et ne déclare donc rien.
    """
    _result, _graph, _vectors, telemetry = _run(_doc())

    assert telemetry.snapshot().unknowns == {"typelien": ["ZORGLUB"]}


def test_embedding_actif_ecrit_les_vecteurs() -> None:
    """Garde-fou de non-régression : le chemin nominal embarque et écrit un vecteur.

    C'est le pendant du test suivant — sans lui, « zéro vecteur quand coupé » pourrait
    passer alors que le pipeline n'en écrit JAMAIS.
    """
    _result, _graph, vectors, _telemetry = _run(_doc(), embedding_enabled=True)

    assert len(vectors.chunks) == 1  # le chunk unique du stub, embarqué et upserté


def test_embedding_coupe_nECRIT_AUCUN_vecteur_mais_merge_le_noeud() -> None:
    """ADR-023 : ``embedding_enabled=False`` saute ``embed()`` — Qdrant reste vide.

    Ce qu'on prouve : AUCUN ``EmbeddedChunk`` n'atteint le dépôt (pas même un vecteur
    nul). Et pourtant le nœud
    Neo4j est mergé et la relation ressort pour la phase 2 : couper l'embedding n'ampute
    que la vectorisation, le reste du régime d'ingestion tourne à l'identique — c'est
    l'état d'itération dev sur le modèle de données sans payer le GPU.
    """
    result, graph, vectors, _telemetry = _run(_doc(), embedding_enabled=False)

    assert vectors.chunks == []  # rien d'embarqué, rien d'upserté
    assert graph.nodes == {SELF.serialize()}  # …mais le nœud est bien écrit
    assert len(result.relations) == 1  # …et la relation part en phase 2, intacte
