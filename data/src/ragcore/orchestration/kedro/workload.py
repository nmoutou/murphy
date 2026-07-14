"""Le workload — le travail d'UN document, tel que le pool le parallélise (§11).

C'est ici que se referme le fil rouge des lots 3 et 4. Trois choses n'existaient
qu'en creux avant ce module, et il les rend concrètes toutes les trois :

1. **Le dernier maillon d'``unknowns``.** Le parser et l'extracteur remontent leurs
   inconnus dans leur *valeur de retour* (``parsed.unknowns``, ``extraction.unknowns``)
   — jamais par une télémétrie, car ils ne tournent pas dans le worker qui réduit
   ``RunStats``. Le workload, LUI, tient une ``WorkerTelemetry`` : c'est donc lui, et
   lui seul, qui *déclare* ces inconnus (``record_unknown``). Sans cet appel, tout le
   tuyau plombé aux lots 3-4 (``record_unknown`` → aggregator → ``RunStats.unknowns``
   → ``RunSummary``) resterait sans producteur.

2. **Le seul appelant de ``extract()`` hors tests.** L'extraction descend dans le
   worker (doctrine §9). ``nodes/persist.py`` était l'ancien appelant ; il est
   supprimé au profit de ce module.

3. **La frontière phase-1/phase-2.** Le workload EXTRAIT les relations mais ne les
   ÉCRIT PAS : il les remonte dans ``WorkloadResult.relations``. Les arêtes sont
   écrites en phase 2 (``ResolveRelationsService``), après que tous les nœuds du run
   existent — sans quoi un ``MATCH`` sur une cible pas encore écrite ferait tomber
   l'arête dans le vide. La saga du ``use_case`` n'écrit donc qu'un NŒUD.
"""

from __future__ import annotations

from collections.abc import Callable

from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.ingestion_runner import DocumentWorkload, WorkloadResult
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import Operation
from ragcore.core.ports.chunker import BaseChunker
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.relation_extractor import BaseRelationExtractor
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import WorkerTelemetry

__all__ = ["UseCaseFactory", "build_document_workload"]

# Fabrique un use case posé sur la télémétrie DU worker. Ce n'est pas un détail : le
# use case tient des dépôts Mongo/Neo4j/Qdrant, et un client Motor est lié à la boucle
# qui l'a touché en premier. Partager une instance entre workers ferait revenir la
# globale ``_LOOP`` sous un autre nom. Chaque worker fabrique donc le sien, sur SA pile.
UseCaseFactory = Callable[[WorkerTelemetry], IngestDocumentUseCase]


def build_document_workload(
    chunker: BaseChunker,
    embedder: BaseEmbedder,
    extractor: BaseRelationExtractor,
    use_case_factory: UseCaseFactory,
    context: PipelineContext,
) -> DocumentWorkload:
    """Fabrique le ``DocumentWorkload`` que le runner injecte à chaque worker.

    Le runner ne connaît ni chunker, ni embedder, ni extracteur : il reçoit une
    fonction ``(parsed, operation, runtime, telemetry) -> WorkloadResult`` et la
    parallélise. ``runtime`` et ``telemetry`` sont ceux du worker courant, fournis par
    le runner — ils ne sont donc PAS capturés ici.

    Le chunker et l'extracteur sont purs, et l'embedder crée son client HTTP *à
    l'appel* (donc sur la bonne boucle) : ils se partagent sans risque. Le use case,
    lui, tient des dépôts liés à une boucle — d'où la ``use_case_factory``, appelée une
    fois PAR worker avec la télémétrie de ce worker.
    """

    # Le use case d'un worker, mémorisé. La fabrique crée TROIS clients (Mongo, Neo4j,
    # Qdrant) : l'appeler par document en créait 1121 jeux au lieu de 4 — ce que sa propre
    # docstring interdisait déjà (« un use case PAR worker »). La clé est la télémétrie,
    # qui est justement l'objet-identité du worker : le runner en construit une par shard.
    use_cases: dict[int, IngestDocumentUseCase] = {}

    def _use_case_for(telemetry: WorkerTelemetry) -> IngestDocumentUseCase:
        key = id(telemetry)
        use_case = use_cases.get(key)
        if use_case is None:
            use_case = use_case_factory(telemetry)
            use_cases[key] = use_case
        return use_case

    def workload(
        parsed: ParsedDocument,
        operation: Operation,
        runtime: AsyncRuntime,
        telemetry: WorkerTelemetry,
    ) -> WorkloadResult:
        # Les inconnus du PARSE, déclarés par le seul qui tient la télémétrie du worker.
        _declare_unknowns(telemetry, parsed.unknowns)

        chunks = chunker.chunk(parsed)
        # ``embed`` est le seul port de traitement asynchrone : le pont sync→async est
        # le runtime DU WORKER (sa boucle, ses clients), jamais une globale (§11).
        embedded = runtime.run(embedder.embed(chunks))

        # Le SEUL appelant de extract() hors tests. Ses inconnus voyagent, eux aussi,
        # dans la donnée — et sont déclarés ici.
        extraction = extractor.extract(parsed)
        _declare_unknowns(telemetry, extraction.unknowns)

        # Le use case du worker — construit UNE fois, réutilisé sur tous ses documents.
        # La saga n'écrit qu'un NŒUD (mongo → qdrant → neo4j:node) ; signature à 4
        # arguments depuis le lot 4 : les relations ne passent plus par le use case.
        use_case = _use_case_for(telemetry)
        runtime.run(use_case.execute(parsed, embedded, operation, context))

        # Les relations ne sont PAS écrites ici : elles remontent vers la phase 2.
        return WorkloadResult(relations=extraction.relations)

    return workload


def _declare_unknowns(
    telemetry: WorkerTelemetry, unknowns: dict[str, list[str]]
) -> None:
    for category, values in unknowns.items():
        for value in values:
            telemetry.record_unknown(category, value)
