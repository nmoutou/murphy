"""Le workload — le travail d'UN document, tel que le pool le parallélise (§11).

C'est ici que se referme le fil rouge des lots 3 et 4. Trois choses n'existaient
qu'en creux avant ce module, et il les rend concrètes toutes les trois :

1. **Le dernier maillon des inconnus d'EXTRACTION.** L'extracteur remonte ses inconnus
   (``typelien``, ``sens``, ``identifiant``) dans sa *valeur de retour*
   (``extraction.unknowns``) — jamais par une télémétrie, car il ne tourne pas dans le
   worker qui réduit ``RunStats``. Le workload, LUI, tient une ``WorkerTelemetry`` :
   c'est donc lui qui les *déclare* (``record_unknown``). Les inconnus de PARSE
   n'existent plus (cadrage B-00-d) : les balises non-configurées sont routées par la
   cascade et signalées au site de parse (``computeIdempotence``).

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


def build_document_workload(  # noqa: PLR0913 — chaque argument est une pièce du workload ; les grouper cacherait ce qu'on assemble
    chunker: BaseChunker,
    embedder: BaseEmbedder,
    extractor: BaseRelationExtractor,
    use_case_factory: UseCaseFactory,
    context: PipelineContext,
    embedding_enabled: bool = True,
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

    ``embedding_enabled=False`` (dev, ADR-023) SAUTE l'embedding : ``embed()`` n'est pas
    appelé, la saga reçoit zéro chunk embarqué, Qdrant n'écrit rien. Mongo et Neo4j
    tournent normalement — c'est l'état recherché pour itérer sur le modèle de données
    sans payer le GPU (~99,9 % du temps d'un run). **Ce n'est PAS ``NoopEmbedder``** :
    lui produit N vecteurs NULS de la bonne dimension et les ÉCRIT dans Qdrant ; couper
    l'embedding n'écrit rien du tout. Le flag est hors du hash de collection (§6) : ne
    pas produire de vecteurs n'invalide aucun vecteur — c'est une décision de régime,
    pas de workflow. La garde ``ENVIRONMENT != dev ⇒ toujours embarquer`` vit dans le
    plan du run (`run_plan.plan_run`), pas ici : ce booléen arrive déjà arbitré.
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
        # Plus d'inconnus de PARSE ici : les balises non-configurées sont ROUTÉES par la
        # cascade du parser (metadata ou lien) et SIGNALÉES au site de parse
        # (computeIdempotence, `tag.unconfigured`) — cadrage B-00-d. Ne restent que les
        # inconnus d'EXTRACTION (typelien/sens/identifiant), déclarés plus bas.

        # L'extraction passe AVANT le chunking, et ce n'est pas un détail d'ordre : c'est
        # elle qui sépare les cibles identifiées (des arêtes) des cibles décrites (des
        # citations). Le document doit porter ses citations AVANT d'être écrit, sinon
        # Mongo et Neo4j reçoivent un document amputé du champ.
        #
        # Le SEUL appelant de extract() hors tests. Ses inconnus voyagent, eux aussi,
        # dans la donnée — et sont déclarés ici.
        extraction = extractor.extract(parsed)
        _declare_unknowns(telemetry, extraction.unknowns)
        if extraction.citations:
            # `ParsedDocument` est gelé : on en dérive une copie. Sans citation, on garde
            # l'instance d'origine — inutile de recopier 1 121 documents pour un tuple vide.
            parsed = parsed.model_copy(
                update={"citations": tuple(extraction.citations)}
            )

        chunks = chunker.chunk(parsed)
        # ``embed`` est le seul port de traitement asynchrone : le pont sync→async est
        # le runtime DU WORKER (sa boucle, ses clients), jamais une globale (§11).
        #
        # Embedding coupé (dev, ADR-023) : on ne calcule RIEN et la saga reçoit une liste
        # vide → le step Qdrant n'a aucun point à écrire. On ne touche pas au chunker : les
        # chunks restent le témoin de ce qu'on aurait embarqué, et Mongo/Neo4j sont écrits
        # à l'identique. C'est un skip, pas un embedder de substitution — voir la docstring.
        embedded = runtime.run(embedder.embed(chunks)) if embedding_enabled else []

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
