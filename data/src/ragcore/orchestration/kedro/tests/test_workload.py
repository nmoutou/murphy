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

from datetime import UTC, datetime

from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.run_context import PipelineContext
from ragcore.core.links import CITES
from ragcore.core.models.chunk import Chunk, EmbeddedChunk
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import Operation, SourceName
from ragcore.core.models.identifiers import ELI, OwnerId
from ragcore.core.models.relation import Relation
from ragcore.core.ports.relation_extractor import ExtractionResult
from ragcore.orchestration.kedro.workload import build_document_workload
from ragcore.tests.fakes import (
    FakeRuntime,
    InMemoryDocumentRepository,
    InMemoryGraphRepository,
    InMemoryManifestRepository,
    InMemoryVectorRepository,
    RecordingTelemetry,
)

OWNER = OwnerId("owner-1")
SELF = ELI(raw="LEGIARTI000000000001")
OTHER = ELI(raw="LEGIARTI000000000002")


def _doc(unknowns: dict[str, list[str]] | None = None) -> ParsedDocument:
    return ParsedDocument(
        identifier=SELF,
        owner_id=OWNER,
        source=SourceName.LEGI,
        title="Article",
        content="Le contenu réel de l'article, en français.",
        structure={},
        metadata={},
        unknowns=unknowns or {},
        parsed_at=datetime.now(UTC),
    )


class _StubChunker:
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        return [
            Chunk(
                chunk_id=f"{document.identifier.raw}_0000",
                parent_identifier=document.identifier,
                owner_id=document.owner_id,
                ordinal=0,
                text=document.content,
                tag_path=[],
                char_start=0,
                char_end=len(document.content),
                metadata={},
            )
        ]


class _StubEmbedder:
    async def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=chunk, embedding=[0.0] * 3, embedding_model="stub", embedding_dim=3
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
                    owner_id=OWNER,
                    source=SourceName.LEGI,
                )
            ],
            unknowns={"typelien": ["ZORGLUB"]},
        )


def _use_case_factory(graph: InMemoryGraphRepository):
    """Fabrique un use case sur le graphe donné — la télémétrie du worker est celle
    que le workload passe. On construit les dépôts en mémoire une fois et on les
    partage : le test ne parallélise pas, la contrainte de boucle ne s'y applique pas.
    """

    def factory(telemetry) -> IngestDocumentUseCase:  # noqa: ANN001
        return IngestDocumentUseCase(
            document_repo=InMemoryDocumentRepository(),
            graph_repo=graph,
            vector_repo=InMemoryVectorRepository(),
            manifest_repo=InMemoryManifestRepository(),
            telemetry=telemetry,
        )

    return factory


def _run(document: ParsedDocument, extractor: _StubExtractor | None = None):
    graph = InMemoryGraphRepository()
    context = PipelineContext.create(owner_id=OWNER, source=SourceName.LEGI)
    workload = build_document_workload(
        chunker=_StubChunker(),
        embedder=_StubEmbedder(),
        extractor=extractor or _StubExtractor(),
        use_case_factory=_use_case_factory(graph),
        context=context,
    )
    runtime = FakeRuntime(worker_id=0)
    telemetry = RecordingTelemetry()
    try:
        result = workload(document, Operation.INSERT, runtime, telemetry)
    finally:
        runtime.close()
    return result, graph, telemetry


def test_les_inconnus_du_parse_et_de_lextraction_sont_DECLARES() -> None:
    """Les deux sources d'inconnus rejoignent l'agrégat du worker.

    ``parsed.unknowns`` vient du parser, ``extraction.unknowns`` de l'extracteur ;
    aucun des deux ne tient la télémétrie. C'est le workload qui les déclare — et
    ``snapshot()`` est la preuve que le tuyau, enfin, coule.
    """
    document = _doc(unknowns={"balise": ["ZORG"]})

    _result, _graph, telemetry = _run(document)

    unknowns = telemetry.snapshot().unknowns
    assert unknowns == {"balise": ["ZORG"], "typelien": ["ZORGLUB"]}


def test_la_phase_1_NECRIT_AUCUNE_arete() -> None:
    """Le nœud est mergé, l'arête ne l'est pas : elle attend la phase 2 (§11).

    Écrire l'arête ici la ferait dépendre de l'ordre d'ingestion : sa cible peut ne
    pas encore être un nœud. On le prouve contre un vrai use case sur un vrai graphe
    en mémoire — pas contre un espion complaisant.
    """
    result, graph, _telemetry = _run(_doc())

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


def test_un_document_sans_inconnu_ne_declare_rien() -> None:
    """Le cas nominal : vocabulaire saturé, ``unknowns`` vide côté parse.

    L'extracteur stub déclare toujours ``ZORGLUB`` ; ce qu'on vérifie ici, c'est
    qu'aucun inconnu FANTÔME n'apparaît côté parse quand le document n'en porte pas.
    """
    _result, _graph, telemetry = _run(_doc(unknowns={}))

    assert telemetry.snapshot().unknowns == {"typelien": ["ZORGLUB"]}
