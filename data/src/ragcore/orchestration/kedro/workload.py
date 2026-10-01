"""Le workload — le travail d'UN document, tel que le pool le parallélise (§11).

C'est ici que se referme le fil rouge des lots 3 et 4. Trois choses n'existaient
qu'en creux avant ce module, et il les rend concrètes toutes les trois :

1. **Le dernier maillon des inconnus d'EXTRACTION.** L'extracteur remonte ses inconnus
   (les ``typelien`` non traduits, sous ``links``) et ses liens perdus dans sa *valeur
   de retour* — jamais par une télémétrie, car il ne tourne pas dans le worker qui
   réduit ``RunStats``. Le workload, LUI, tient une ``WorkerTelemetry`` : c'est donc lui
   qui les *déclare* (``record_unknown``, ``relation.unknown``). Les signaux de PARSE
   (``tags``, liens heuristiques, ``roots``) sont déclarés au site de parse
   (``parseDocuments``).

2. **Le seul appelant de ``extract()`` hors tests.** L'extraction descend dans le
   worker (doctrine §9). ``nodes/persist.py`` était l'ancien appelant ; il est
   supprimé au profit de ce module.

3. **La frontière phase-1/phase-2.** Le workload EXTRAIT les relations mais ne les
   ÉCRIT PAS : il les remonte dans ``WorkloadResult.relations``. Les arêtes sont
   écrites en phase 2 (``ResolveRelationsService``), après que tous les nœuds du run
   existent — sans quoi un ``MATCH`` sur une cible pas encore écrite ferait tomber
   l'arête dans le vide. La saga du ``use_case`` n'écrit donc qu'un NŒUD, plus les
   relations non formatées du document (leur cible n'est pas un nœud : rien à attendre).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.ingestion_runner import DocumentWorkload, WorkloadResult
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.unknown_tally import UnknownExample
from ragcore.core.ports.chunker import BaseChunker
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.core.ports.relation_extractor import (
    BaseRelationExtractor,
    ExtractionResult,
)
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.telemetry_events import PAYLOAD_COUNT_KEY, RELATION_UNKNOWN

__all__ = ["UseCaseFactory", "WorkloadSteps", "build_document_workload"]

# Fabrique un use case posé sur la télémétrie DU worker. Ce n'est pas un détail : le
# use case tient des dépôts Mongo/Neo4j/Qdrant, et un client Motor est lié à la boucle
# qui l'a touché en premier. Partager une instance entre workers ferait revenir la
# globale ``_LOOP`` sous un autre nom. Chaque worker fabrique donc le sien, sur SA pile.
UseCaseFactory = Callable[[WorkerTelemetry], IngestDocumentUseCase]


@dataclass(frozen=True)
class WorkloadSteps:
    """Les trois traitements d'un document, partagés entre les workers.

    Le chunker et l'extracteur sont purs, et l'embedder crée son client HTTP *à l'appel*
    (donc sur la bonne boucle) : ils se partagent sans risque.
    """

    chunker: BaseChunker
    embedder: BaseEmbedder
    extractor: BaseRelationExtractor


def build_document_workload(
    steps: WorkloadSteps,
    use_case_factory: UseCaseFactory,
    context: PipelineContext,
    embedding_enabled: bool = True,
) -> DocumentWorkload:
    """Fabrique le ``DocumentWorkload`` que le runner injecte à chaque worker.

    Le runner ne connaît ni chunker, ni embedder, ni extracteur : il reçoit une
    fonction ``(parsed, runtime, telemetry) -> WorkloadResult`` et la
    parallélise. ``runtime`` et ``telemetry`` sont ceux du worker courant, fournis par
    le runner — ils ne sont donc PAS capturés ici.

    Les ``steps`` se partagent sans risque (cf. ``WorkloadSteps``). Le use case, lui,
    tient des dépôts liés à une boucle — d'où la ``use_case_factory``, appelée une
    fois PAR worker avec la télémétrie de ce worker.

    ``embedding_enabled=False`` (dev, ADR-023) SAUTE l'embedding : ``embed()`` n'est pas
    appelé, la saga reçoit zéro chunk embarqué, Qdrant n'écrit rien. Mongo et Neo4j
    tournent normalement — c'est l'état recherché pour itérer sur le modèle de données
    sans payer le GPU (~99,9 % du temps d'un run). La garde ``ENVIRONMENT != dev ⇒
    toujours embarquer`` vit dans le plan du run (`run_plan.plan_run`), pas ici : ce
    booléen arrive déjà arbitré.
    """
    use_cases = _UseCasePerWorker(use_case_factory)

    def workload(
        parsed: ParsedDocument,
        runtime: AsyncRuntime,
        telemetry: WorkerTelemetry,
    ) -> WorkloadResult:
        # Les signaux de PARSE sont déclarés au site de parse (parseDocuments). Ne restent
        # que ceux d'EXTRACTION — typelien inconnus, liens perdus — déclarés par
        # `_extract`.
        extraction = _extract(steps.extractor, parsed, telemetry, context)

        chunks = steps.chunker.chunk(parsed)
        # ``embed`` est le seul port de traitement asynchrone : le pont sync→async est
        # le runtime DU WORKER (sa boucle, ses clients), jamais une globale (§11).
        #
        # Embedding coupé (dev, ADR-023) : on ne calcule RIEN et la saga reçoit une liste
        # vide → le step Qdrant n'a aucun point à écrire. On ne touche pas au chunker : les
        # chunks restent le témoin de ce qu'on aurait embarqué, et Mongo/Neo4j sont écrits
        # à l'identique. C'est un skip, pas un embedder de substitution — voir la docstring.
        embedded = (
            runtime.run(steps.embedder.embed(chunks)) if embedding_enabled else []
        )

        # Le use case du worker — construit UNE fois, réutilisé sur tous ses documents.
        # La saga n'écrit qu'un NŒUD (mongo → qdrant → neo4j:node) et les relations non
        # formatées du document : les relations, elles, ne passent pas par le use case.
        use_case = use_cases.for_worker(telemetry)
        runtime.run(
            use_case.execute(
                parsed, embedded, context, extraction.unformatted_relations
            )
        )

        # Les relations ne sont PAS écrites ici : elles remontent vers la phase 2.
        return WorkloadResult(relations=extraction.relations)

    return workload


class _UseCasePerWorker:
    """Le use case de chaque worker, mémorisé.

    La fabrique crée TROIS clients (Mongo, Neo4j, Qdrant) : l'appeler par document en
    créait 1121 jeux au lieu de 4 — ce que sa propre docstring interdisait déjà (« un use
    case PAR worker »). La clé est la télémétrie, qui est justement l'objet-identité du
    worker : le runner en construit une par shard.
    """

    def __init__(self, factory: UseCaseFactory) -> None:
        self._factory = factory
        self._use_cases: dict[int, IngestDocumentUseCase] = {}

    def for_worker(self, telemetry: WorkerTelemetry) -> IngestDocumentUseCase:
        key = id(telemetry)
        use_case = self._use_cases.get(key)
        if use_case is None:
            use_case = self._factory(telemetry)
            self._use_cases[key] = use_case
        return use_case


def _extract(
    extractor: BaseRelationExtractor,
    parsed: ParsedDocument,
    telemetry: WorkerTelemetry,
    context: PipelineContext,
) -> ExtractionResult:
    """Extrait les liens du document, déclare ses inconnus et compte ses liens perdus.

    L'extraction sépare les cibles identifiées (des arêtes, pour la phase 2) des cibles
    décrites (des relations non formatées, que la saga du document écrit). Ni les unes
    ni les autres ne touchent le document : il est écrit tel que le parser l'a produit.

    Le SEUL appelant de extract() hors tests. Ses inconnus voyagent, eux aussi, dans la
    donnée — et sont déclarés ici.
    """
    extraction = extractor.extract(parsed)
    _declare_unknowns(telemetry, extraction.unknowns, parsed)
    if extraction.lost_links:
        telemetry.emit(
            build_event(
                event_type=RELATION_UNKNOWN,
                run_id=context.run_id,
                source=parsed.source,
                document_id=parsed.identifier.serialize(),
                payload={PAYLOAD_COUNT_KEY: extraction.lost_links},
            )
        )
    return extraction


def _declare_unknowns(
    telemetry: WorkerTelemetry,
    unknowns: dict[str, list[str]],
    parsed: ParsedDocument,
) -> None:
    """L'exemple est le document : l'extracteur ne dit pas de quelle facette vient le
    lien, on donne donc son premier fichier."""
    example = UnknownExample(
        identifier=parsed.identifier.serialize(),
        source_file=parsed.source_files[0] if parsed.source_files else "",
    )
    for category, values in unknowns.items():
        for value in values:
            telemetry.record_unknown(category, value, example)
