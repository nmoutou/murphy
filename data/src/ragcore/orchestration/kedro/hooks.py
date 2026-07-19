"""Kedro hooks: pipeline lifecycle wiring for ragcore."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog

from ragcore.adapters.config.settings import (
    get_embedding_runtime_settings,
    get_infra_settings,
)
from ragcore.adapters.embedding.local_embedder import LocalEmbedder
from ragcore.adapters.embedding.noop_embedder import NoopEmbedder
from ragcore.adapters.embedding.openai_embedder import (
    OpenAIEmbedder,
    assert_service_serves_model,
)
from ragcore.adapters.runtime import AsyncioRuntime, AsyncioRuntimeFactory
from ragcore.adapters.storage.mongo.audit_repository import MongoAuditRepository
from ragcore.adapters.storage.mongo.client import create_mongo_client
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.manifest_repository import MongoManifestRepository
from ragcore.adapters.storage.mongo.pending_repository import (
    MongoPendingRelationRepository,
)
from ragcore.adapters.storage.mongo.published_collection_repository import (
    MongoPublishedCollectionRepository,
)
from ragcore.adapters.storage.mongo.run_summary_repository import (
    MongoRunSummaryRepository,
)
from ragcore.adapters.storage.mongo.schemas import (
    ensure_data_indexes,
    ensure_meta_indexes,
)
from ragcore.adapters.storage.neo4j.client import create_neo4j_driver
from ragcore.adapters.storage.neo4j.graph_repository import (
    Neo4jGraphRepository,
    NodeHydration,
)
from ragcore.adapters.storage.qdrant.client import create_qdrant_client
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.adapters.telemetry import (
    JsonlFileTelemetry,
    MongoAuditTelemetryAdapter,
    RunStatsAggregator,
)
from ragcore.adapters.telemetry.factory import (
    WorkerTelemetryFactory,
    assemble_telemetry,
)
from ragcore.adapters.telemetry.registry_aware import RegistryAwareTelemetry
from ragcore.adapters.tracking import build_experiment_tracker
from ragcore.application.ingest_document import IngestDocumentUseCase
from ragcore.application.ingestion_runner import IngestionRunner
from ragcore.application.resolve_relations import ResolveRelationsService
from ragcore.application.run_context import PipelineContext
from ragcore.core.config import (
    ChunkingConfig,
    EmbeddingConfig,
    NormalizationConfig,
    WorkflowConfig,
    collection_name,
)
from ragcore.core.models.audit import build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.published_collection import PublishedCollection
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.experiment_tracker import ExperimentTracker
from ragcore.core.ports.telemetry import WorkerTelemetry
from ragcore.core.services.run_artifacts import run_scoped_filename
from ragcore.core.services.telemetry_registry import TelemetryRegistry
from ragcore.core.telemetry_events import (
    CHUNK_TRUNCATED,
    DOCUMENT_PERSISTED,
    EVENT_CATALOG,
    PIPELINE_RUN_COMPLETED,
    PIPELINE_RUN_FAILED,
    PIPELINE_RUN_STARTED,
)
from ragcore.orchestration.kedro.workload import build_document_workload
from ragcore.sources.composite import (
    CompositeConnector,
    RoutingParser,
    RoutingRelationExtractor,
)
from ragcore.sources.generic import (
    GenericParser,
    GenericRelationExtractor,
    StructuralChunker,
)
from ragcore.sources.registry import all_sources, definition_for

logger = logging.getLogger(__name__)

# Le pool de la phase 1. Un jour un paramètre ; pour l'instant une constante nommée,
# et non un « 4 » nu perdu dans le constructeur du runner.
#
# **Ne pas l'augmenter en espérant un gain : c'est mesuré, ça n'en donne pas.** 99,9 % du
# temps d'un document part dans l'embedding (parse 0,9 ms, chunk 0,1 ms, embed 1364 ms),
# et le mur est le GPU lui-même, pas le nombre de requêtes qu'on lui envoie. Un banc
# d'essai isolé promettait ×4 en passant à 16 workers ; le run réel n'a rien gagné
# (751 s → 738 s). Le seul levier réel est de calculer MOINS de vecteurs, c.-à-d.
# `chunk_size` (cf. la note de perf dans ETAT.md).
_WORKER_COUNT = 4


class TelemetryHooks:
    def __init__(self) -> None:
        self._telemetry: RegistryAwareTelemetry | None = None
        self._aggregator: RunStatsAggregator | None = None
        self._context: PipelineContext | None = None
        self._stats_dir: Path | None = None
        self._summary_repo: MongoRunSummaryRepository | None = None
        self._published_repo: MongoPublishedCollectionRepository | None = None
        self._qdrant_collection: str | None = None
        """L'empreinte que ce run écrit. Retenue ici pour être PUBLIÉE si le run est `ok`.

        Elle est déjà dérivée en tête de run (``collection_name(workflow)``) ; la garder
        évite une seconde dérivation, et deux dérivations sont deux occasions de diverger.
        """
        self._embedder: object | None = None
        self._runtime_instance: AsyncioRuntime | None = None
        self._tracker: ExperimentTracker | None = None
        """Le tracker d'expériences (§9). Ouvert en tête de run, fermé en fin — dans
        `after_pipeline_run` ET `on_pipeline_error`, pour qu'un run cassé ne laisse pas
        un run MLflow ouvert que le suivant viendrait polluer. `noop` par défaut."""

    @property
    def _runtime(self) -> AsyncioRuntime:
        """Le runtime du HOOK — le sien, pas une boucle globale. Les workers ont le leur.

        **Construit au premier usage, jamais dans `__init__`.** `settings.py` instancie
        `TelemetryHooks()` à l'IMPORT du module, et Kedro `deepcopy` ses settings — donc
        les hooks — quand il ouvre une session (`KedroSession._init_store`). Une boucle
        asyncio n'est pas copiable : allouée dans `__init__`, elle faisait échouer
        `kedro run` avec `TypeError: cannot pickle '_contextvars.Context'` **avant même
        que le pipeline démarre**.

        Un `__init__` pose des attributs ; il n'alloue pas de ressource système. Ici la
        règle n'est pas un principe abstrait — c'est la différence entre un pipeline qui
        se lance et un pipeline qui ne se lance pas.
        """
        if self._runtime_instance is None:
            self._runtime_instance = AsyncioRuntimeFactory().build(worker_id=-1)
        return self._runtime_instance

    @hook_impl
    def before_pipeline_run(  # noqa: PLR0915 — pur câblage : construire les clients puis POSER chaque objet au catalogue est un inventaire, pas de la logique ; le fractionner disperserait l'assemblage
        self, run_params: dict[str, Any], catalog: DataCatalog
    ) -> None:
        settings = get_infra_settings()
        embedding_settings = get_embedding_runtime_settings()

        # Charger les paramètres Kedro (parameters.yml). PAS de fallback silencieux
        # vers `{}` : `_build_workflow_config({})` produirait la config par DÉFAUT
        # (chunk_size=128…), donc un `collection_name` par défaut — et le run
        # écrirait tout le corpus dans une collection nommée d'après une stratégie
        # que l'utilisateur n'a pas choisie, en écrasant potentiellement l'A/B d'un
        # autre run. Un config illisible n'est pas un run par défaut : c'est un run
        # qu'on ARRÊTE, avec une erreur claire (fail-fast, cf. doctrine du projet).
        try:
            params = catalog.load("parameters")
        except Exception as exc:
            raise RuntimeError(
                "Impossible de charger `parameters.yml` : le run est interrompu. "
                "Continuer avec les défauts baptiserait la collection Qdrant d'après "
                "une config que personne n'a choisie — une perte silencieuse de la "
                "stratégie d'ingestion."
            ) from exc

        # La config de workflow — LA référence (§9). `parameters.yml` n'est qu'une façon
        # de la peupler : c'est ici que Kedro cesse d'être la vérité et redevient un
        # shell. Un CLI ou un test construit le même objet sans qu'aucun YAML n'existe.
        workflow = _build_workflow_config(params)

        # La collection Qdrant est DÉRIVÉE, plus configurée (§6). Elle porte l'empreinte
        # de ce qui produit les vecteurs : changer le chunk_size crée mécaniquement une
        # collection neuve, et les deux coexistent — c'est ce qui rend l'A/B possible.
        # Un `collection:` écrit à la main dans le YAML permettait au contraire d'écraser
        # les vecteurs d'une stratégie avec ceux d'une autre, sans que rien ne le signale.
        qdrant_collection = collection_name(workflow)
        logger.info(
            "Collection Qdrant dérivée de la config de workflow : %s", qdrant_collection
        )

        # Le tracking d'expériences (§9). Le run-id EST le nom de collection — donc le
        # fingerprint du workflow — parce que `collection_name` n'est rien d'autre que
        # `fingerprint` : les deux ne peuvent pas diverger, ils sortent du même calcul.
        # C'est ce qui lie le run MLflow à sa collection Qdrant, et lève l'opacité du
        # hash en portant la `WorkflowConfig` en clair. `noop` par défaut : aucun serveur
        # requis, aucune dépendance ajoutée au chemin critique.
        self._tracker = build_experiment_tracker(settings)
        self._tracker.start_run(RunId(qdrant_collection), workflow)

        # Le modèle qui vient de BAPTISER la collection est-il celui que le service SERT ?
        #
        # TEI ne sert qu'un modèle — celui de son `--model-id` — et ignore le champ `model`
        # de la requête. Si le conteneur et `parameters.yml` divergent, on écrit les
        # vecteurs d'un modèle dans la collection nommée d'après un autre : rien ne lève,
        # rien ne loggue, et ça ne se voit qu'à la recherche.
        #
        # C'est une PRÉCONDITION du run, et c'est pourquoi elle est ici et pas dans
        # l'embedder : `SagaExecutor` attrape `Exception` pour compenser, donc levée dans
        # un worker elle deviendrait un échec par document — compensé N fois, avec un run
        # qui conclut « ok ». Vérifier N fois quel modèle le service sert n'aurait de toute
        # façon aucun sens : il n'en sert qu'un, et il le dit une fois pour toutes.
        if embedding_settings.provider == "openai":
            self._runtime.run(
                assert_service_serves_model(
                    embedding_settings.service_url or "",
                    workflow.embedding.model_name,
                )
            )
        elif embedding_settings.provider == "noop":
            # `provider` n'entre PAS dans l'empreinte (§6) : deux façons d'atteindre le
            # même modèle produisent les mêmes vecteurs. Mais `noop` n'atteint aucun
            # modèle — il produit des vecteurs NULS, et les écrit dans la collection du
            # vrai modèle, où plus rien ne les distingue ensuite. La doctrine assume la
            # verrue ; elle n'exige pas qu'elle soit muette.
            logger.warning(
                "EMBEDDING_PROVIDER=noop : les vecteurs seront NULS et seront écrits dans "
                "la collection %s — celle du vrai modèle, où rien ne les distinguera. "
                "Hygiène de test uniquement : pour un vrai run, EMBEDDING_PROVIDER=openai.",
                qdrant_collection,
            )

        # Infrastructure clients
        mongo_client = create_mongo_client(settings.mongodb_uri)
        neo4j_driver = create_neo4j_driver(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password.get_secret_value(),
        )
        qdrant_client = create_qdrant_client(
            settings.qdrant_url,
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None,
        )

        # Créer les indexes MongoDB
        data_db = settings.mongodb_data_db_name
        meta_db = settings.mongodb_meta_db_name
        self._runtime.run(ensure_data_indexes(mongo_client[data_db]))
        self._runtime.run(ensure_meta_indexes(mongo_client[meta_db]))

        # Repositories du HOOK — posés sur SA boucle (self._runtime). Ils servent les
        # nœuds de maintenance (nukeAll, connect, computeIdempotence) et la phase 2,
        # qui ne sont pas parallélisés. Les WORKERS de la phase 1 fabriquent LES LEURS
        # (cf. use_case_factory plus bas) : un dépôt Mongo est lié à la boucle qui l'a
        # touché en premier, donc partager ceux-ci avec les workers ferait revenir la
        # globale ``_LOOP`` sous un autre nom (§11).
        # L'hydratation des nœuds Neo4j (ADR-022 §2, toggles redéfinis) : résolue UNE
        # fois, partagée entre le dépôt du hook et ceux des workers — deux résolutions
        # seraient deux occasions de diverger.
        node_hydration = _resolve_node_hydration(params, settings.environment)

        doc_repo = MongoDocumentRepository(mongo_client, data_db)
        manifest_repo = MongoManifestRepository(mongo_client, data_db)
        audit_repo = MongoAuditRepository(mongo_client, meta_db)
        summary_repo = MongoRunSummaryRepository(mongo_client, meta_db)
        published_repo = MongoPublishedCollectionRepository(mongo_client, meta_db)
        pending_repo = MongoPendingRelationRepository(mongo_client, meta_db)
        graph_repo = Neo4jGraphRepository(neo4j_driver, node_hydration)
        vector_repo = QdrantVectorRepository(
            qdrant_client, qdrant_collection, workflow.embedding.dimension
        )

        # Pipeline context (created early so telemetry adapters can use the run_id)
        extra = run_params.get("extra_params") or {}
        owner_id = extra.get("owner_id", settings.owner_id)

        # Les SOURCES du run. Un run nu les ingère TOUTES ; on peut le restreindre :
        #
        #     kedro run                          → les six sources
        #     kedro run --params source=cass     → CASS seule
        #     kedro run --params source=cass,jade → CASS et JADE
        #
        # **Ce que ça change, et qu'il faut assumer.** L'ancienne règle « une seule source
        # par run » protégeait la lisibilité du bilan : un run qui mélange deux sources doit
        # pouvoir dire *laquelle* a échoué.
        #
        # ⚠️ DETTE OUVERTE : il ne le peut pas encore. `RunStats.breakdowns` ne ventile que
        # `reason` et `operation` (cf. `adapters/telemetry/aggregator.py`), PAS la source.
        # Un run à six sources rend donc un bilan agrégé où l'échec est anonyme quant à sa
        # provenance. La restriction par paramètre garde la voie du rejeu ciblé ouverte,
        # mais le bilan ne dit pas encore *quoi* rejouer.
        sources = _resolve_sources(extra.get("source", settings.source))
        definitions = {source: definition_for(source) for source in sources}

        # `source=None` dans le contexte signifie « ce run n'est pas mono-source ». Le
        # modèle le prévoyait déjà (`SourceName | None`) : la porte était ouverte, on ne
        # force rien. Un run mono-source garde SA source dans le contexte — les événements
        # qu'il émet restent donc attribuables exactement comme avant.
        self._context = PipelineContext.create(
            owner_id=OwnerId(owner_id),
            source=sources[0] if len(sources) == 1 else None,
        )
        logger.info(
            "Sources du run (%d) : %s",
            len(sources),
            ", ".join(s.value for s in sources),
        )

        # Telemetry stack — configurable par registry
        meta_root = Path(settings.meta_jsonl_dir)

        # Registry construit depuis le catalogue Python — source de vérité unique
        registry = TelemetryRegistry.from_catalog(EVENT_CATALOG)

        jsonl_telemetry = JsonlFileTelemetry(
            events_dir=meta_root / "events",
            run_id=self._context.run_id,
            started_at=self._context.started_at,
        )
        self._stats_dir = meta_root / "stats"
        self._stats_dir.mkdir(parents=True, exist_ok=True)
        self._summary_repo = summary_repo
        self._published_repo = published_repo
        self._qdrant_collection = qdrant_collection
        self._aggregator = RunStatsAggregator(
            run_id=self._context.run_id,
            owner_id=self._context.owner_id,
            source=self._context.source,
            started_at=self._context.started_at,
        )
        self._telemetry = assemble_telemetry(
            registry,
            jsonl=jsonl_telemetry,
            mongo=MongoAuditTelemetryAdapter(audit_repo, self._runtime),
            aggregate=self._aggregator,
        )

        # **Aucun nom de source ici.** Le parser, le chunker et l'extracteur sont
        # génériques (§3) ; les connecteurs viennent du registre. Ce bloc est identique
        # pour LEGI et pour les cinq juri — c'est très exactement la mesure du succès :
        # ajouter une source n'a demandé aucune ligne dans le hook.
        #
        # Une brique PAR source (chacune a sa table de rôles — elles sont quatre
        # distinctes), et un routeur au-dessus qui aiguille sur `document.source`. Les
        # nœuds, eux, ne voient qu'un connecteur et qu'un parser : les routeurs respectent
        # les mêmes ports, donc le DAG ignore qu'il y a six sources derrière.
        #
        # Purs (chunker, parser, extracteur) ou créant leur client à l'appel (embedder) :
        # partageables entre workers sans risque.
        xml_root = Path(settings.xml_source_path)
        connector = CompositeConnector(
            {
                source: definition.connector(xml_root / definition.subdirectory)
                for source, definition in definitions.items()
            }
        )
        parser = RoutingParser(
            {
                source: GenericParser(definition.table, source)
                for source, definition in definitions.items()
            }
        )
        chunker = StructuralChunker(
            max_chunk_size=workflow.chunking.size, overlap=workflow.chunking.overlap
        )
        relation_extractor = RoutingRelationExtractor(
            {
                source: GenericRelationExtractor(definition.table, source)
                for source, definition in definitions.items()
            }
        )

        # Embedding : le MODÈLE et la DIMENSION viennent du workflow (ils décident des
        # vecteurs, donc ils sont hashés) ; le PROVIDER et son transport viennent de
        # l'infra (ils ne changent aucun vecteur). La couture passe exactement ici.
        embedding = workflow.embedding
        if embedding_settings.provider == "local":
            embedder: object = LocalEmbedder(
                model_name=embedding.model_name,
                dimension=embedding.dimension,
            )
        elif embedding_settings.provider == "noop":
            embedder = NoopEmbedder(dimension=embedding.dimension)
        else:
            embedder = OpenAIEmbedder(
                api_key=embedding_settings.api_key,
                model_name=embedding.model_name,
                dimension=embedding.dimension,
                batch_size=embedding_settings.batch_size,
                base_url=embedding_settings.service_url,
            )
        # Gardé pour l'interroger en fin de run : un chunk qu'il a dû raccourcir pour tenir
        # dans la fenêtre du modèle est un chunk dont la fin n'est PAS indexée. Le document
        # est sauvé, le run est complet — mais le bilan doit le dire.
        self._embedder = embedder

        # L'interrupteur d'embedding (dev, ADR-023). Lu du YAML, mais ARBITRÉ par
        # l'environnement : en dehors de `dev`, on embarque TOUJOURS, quoi que dise le
        # flag. Un flag oublié à `false` dans un `parameters.yml` ne doit pas pouvoir
        # produire une collection Qdrant vide en prod — même logique de garde que
        # `nuke_all` (le défaut penche vers le comportement sûr, pas vers l'économie).
        embedding_enabled = _resolve_embedding_enabled(params, settings.environment)
        if not embedding_enabled:
            logger.warning(
                "EMBEDDING COUPÉ (dev, ADR-023) : aucun vecteur ne sera calculé ni écrit "
                "dans Qdrant. Mongo et Neo4j sont peuplés normalement — régime d'itération "
                "sur le modèle de données. La collection %s restera vide pour ce run.",
                qdrant_collection,
            )

        # --- Le pool de la phase 1 : des FABRIQUES, pas des instances (§11) ---------
        runner = self._build_runner(
            chunker,
            embedder,
            relation_extractor,
            qdrant_collection,
            workflow,
            embedding_enabled,
            node_hydration,
        )

        # --- La phase 2 : un service unique, sur la boucle DU HOOK (pas parallélisé) -
        resolve_service = ResolveRelationsService(
            graph_repo=graph_repo,
            pending_repo=pending_repo,
            telemetry=self._telemetry,
        )

        # Populate catalog for node injection
        catalog.save("connector", connector)
        catalog.save("parser", parser)
        catalog.save("manifest_repo", manifest_repo)
        catalog.save("doc_repo", doc_repo)
        catalog.save("graph_repo", graph_repo)
        catalog.save("vector_repo", vector_repo)
        catalog.save("runner", runner)
        catalog.save("resolve_service", resolve_service)
        catalog.save("pipeline_context", self._context)
        catalog.save("telemetry", self._telemetry)
        # L'agrégat du run, injecté comme les autres objets. C'est le node `report` qui y
        # POUSSE les stats des phases : le hook ne peut pas les tirer du catalogue après
        # coup, Kedro y libère les MemoryDataset dès leur dernier lecteur (cf. `absorb`).
        catalog.save("run_stats_sink", self)
        # Le runtime du hook, injecté aux nœuds non parallélisés (maintenance + phase 2)
        # comme pont sync→async — l'équivalent déclaré de l'ancienne globale run_async.
        catalog.save("pipeline_runtime", self._runtime)

        self._telemetry.emit(
            build_event(
                event_type=PIPELINE_RUN_STARTED,
                run_id=self._context.run_id,
                owner_id=self._context.owner_id,
                source=self._context.source,
                payload={"pipeline": run_params.get("pipeline_name", "__default__")},
            )
        )

    def _build_runner(  # noqa: PLR0913 — chaque argument est une pièce du pool ; les grouper cacherait ce qu'on assemble
        self,
        chunker: StructuralChunker,
        embedder: object,
        extractor: RoutingRelationExtractor,
        qdrant_collection: str,
        workflow: WorkflowConfig,
        embedding_enabled: bool,
        node_hydration: NodeHydration,
    ) -> IngestionRunner:
        """Assemble le pool de la phase 1 : deux fabriques + un use case PAR worker.

        Extrait de ``before_pipeline_run`` pour tenir en un bloc cohérent — c'est ici
        que se joue tout le §11. ``self._context`` est déjà posé quand cette méthode
        est appelée. ``qdrant_collection`` est **dérivé du ``workflow``** (§6) et DOIT
        être celui du ``vector_repo`` du hook — d'où le passage explicite plutôt qu'un
        second appel à ``collection_name`` : deux dérivations, c'est deux occasions de
        diverger, et workers et phase 2 écriraient alors dans deux collections.
        """
        settings = get_infra_settings()
        data_db = settings.mongodb_data_db_name
        meta_db = settings.mongodb_meta_db_name
        events_dir = Path(settings.meta_jsonl_dir) / "events"
        context = self._context
        assert context is not None  # posé en tête de before_pipeline_run

        runtime_factory = AsyncioRuntimeFactory()
        telemetry_factory = WorkerTelemetryFactory(
            run_id=context.run_id,
            owner_id=context.owner_id,
            source=context.source,
            started_at=context.started_at,
            events_dir=events_dir,
            audit_repo_factory=lambda runtime: MongoAuditRepository(
                create_mongo_client(settings.mongodb_uri), meta_db
            ),
        )

        def use_case_factory(telemetry: WorkerTelemetry) -> IngestDocumentUseCase:
            """Un use case PAR worker, sur des dépôts NEUFS et sa propre télémétrie.

            Les clients sont recréés ici : un client Motor/Neo4j/Qdrant est lié à la
            boucle du worker qui l'appelle en premier. Réutiliser ceux du hook les
            lierait à la boucle du hook, et tous les workers échoueraient sauf un.
            """
            worker_mongo = create_mongo_client(settings.mongodb_uri)
            worker_neo4j = create_neo4j_driver(
                settings.neo4j_uri,
                settings.neo4j_username,
                settings.neo4j_password.get_secret_value(),
            )
            worker_qdrant = create_qdrant_client(
                settings.qdrant_url,
                settings.qdrant_api_key.get_secret_value()
                if settings.qdrant_api_key
                else None,
            )
            return IngestDocumentUseCase(
                document_repo=MongoDocumentRepository(worker_mongo, data_db),
                graph_repo=Neo4jGraphRepository(worker_neo4j, node_hydration),
                vector_repo=QdrantVectorRepository(
                    worker_qdrant, qdrant_collection, workflow.embedding.dimension
                ),
                manifest_repo=MongoManifestRepository(worker_mongo, data_db),
                telemetry=telemetry,
            )

        workload = build_document_workload(
            chunker=chunker,
            embedder=embedder,  # type: ignore[arg-type]
            extractor=extractor,
            use_case_factory=use_case_factory,
            context=context,
            embedding_enabled=embedding_enabled,
        )
        return IngestionRunner(
            workload=workload,
            runtime_factory=runtime_factory,
            telemetry_factory=telemetry_factory,
            worker_count=_WORKER_COUNT,
        )

    def absorb(self, stats: RunStats) -> None:
        """Reçoit l'agrégat d'une PHASE. **Sans ça, le bilan ment.**

        Chaque worker tient son propre ``RunStats`` (§11) ; ``IngestionRunner`` les réduit
        et les rend dans ``IngestionOutcome.stats``. Mais ce résultat repartait dans un
        ``MemoryDataset`` que **personne ne lisait** : le hook finalisait *son* agrégateur,
        qui n'avait vu que les events du process principal. Le ``document.persisted`` des
        workers — et surtout leurs **compensations** — n'atteignaient jamais le RunSummary,
        donc ``_status_from`` rendait *toujours* ``ok``.

        **Pourquoi le DAG POUSSE au lieu que le hook TIRE.** J'ai d'abord fait lire le
        catalogue au hook en ``after_pipeline_run``. C'était faux, et silencieusement :
        Kedro **libère** un ``MemoryDataset`` dès son dernier consommateur
        (``_release_datasets``). ``ingestion_outcome`` meurt donc avec le node ``report``,
        et le ``load()`` d'après-run échoue. Le catalogue n'est pas un lieu de rendez-vous
        post-run — c'est un tuyau entre nodes, et il se vide derrière eux.
        """
        if self._aggregator is not None:
            self._aggregator.absorb(stats)

    def _declare_truncations(self) -> None:
        """Un chunk raccourci n'est pas une perte, mais ce n'est pas rien : il se DÉCLARE.

        Le document est ingéré (donc l'équation de complétude tombe juste, à raison), mais
        la fin du chunk n'est pas indexée. Un compteur non nul veut dire une seule chose :
        **le `chunk_size` configuré n'est pas compatible avec la fenêtre du modèle**. Le
        run est sauvé ; la configuration, elle, est à corriger.
        """
        truncations = getattr(self._embedder, "truncations", 0)
        if not truncations or self._telemetry is None or self._context is None:
            return
        self._telemetry.emit(
            build_event(
                event_type=CHUNK_TRUNCATED,
                run_id=self._context.run_id,
                owner_id=self._context.owner_id,
                source=self._context.source,
                payload={"count": truncations},
            )
        )
        logger.warning(
            "%d chunk(s) raccourci(s) pour tenir dans la fenêtre du modèle. Le corpus est "
            "complet, mais la fin de ces chunks n'est pas indexée : baisser `chunk_size`.",
            truncations,
        )

    def _drain_and_declare(self) -> None:
        """Attend les écritures d'audit en vol, et DÉCLARE celles qui ont échoué.

        À appeler avant ``_persist_run_summary`` : le compte doit entrer dans l'agrégat
        pour que ``_status_from`` le voie. Après, le bilan est déjà écrit.

        Le drain n'est pas la fermeture — ``_persist_run_summary`` a encore besoin de la
        boucle (il y écrit le sommaire, de façon *synchrone* : il n'y laisse donc rien en
        vol). C'est bien pour ça que le port sépare ``drain()`` de ``close()``.
        """
        report = self._runtime.drain()
        if not report.failed:
            return
        if self._aggregator is not None:
            self._aggregator.record_audit_failure("drain", report.failed)
        logger.error(
            "%d écriture(s) d'audit PERDUE(S) : le bilan de ce run repose sur des "
            "compteurs incomplets — il est déclaré `degraded`.",
            report.failed,
        )

    def _persist_run_summary(
        self, status: str, error_message: str | None = None
    ) -> RunSummary | None:
        """Finalise l'agrégateur et persiste le RunSummary (fichier JSON + Mongo).

        Rend le bilan : le statut annoncé n'est **pas** celui qui sort (``finalize``
        le re-dérive des compteurs). L'appelant qui veut savoir si le run est vraiment
        `ok` — pour publier, par exemple — doit lire le bilan, pas ce qu'il a demandé.
        """
        if (
            self._aggregator is None
            or self._stats_dir is None
            or self._summary_repo is None
        ):
            return None
        summary = self._aggregator.finalize(status=status, error_message=error_message)  # type: ignore[arg-type]
        path = self._stats_dir / run_scoped_filename(
            summary.run_id, summary.started_at, ".json"
        )
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._runtime.run(self._summary_repo.upsert(summary))
        return summary

    def _publish_collection(self, summary: RunSummary | None) -> None:
        """Publie l'empreinte de ce run — **si et seulement si** le run est `ok`.

        C'est ici que l'équation de complétude cesse d'être un outil de diagnostic pour
        devenir **la condition de publication**. Un run `degraded` a laissé un corpus
        incomplet : publier son empreinte propagerait la fuite jusqu'à l'utilisateur, qui
        n'aurait aucun moyen de le savoir. Le corpus précédent, lui, était complet — le
        pointeur ne bouge pas, et le serving continue de servir le dernier bon.

        Le statut est LU dans le bilan, jamais re-dérivé : deux dérivations sont deux
        occasions de diverger, et celle-ci déciderait de ce que voit l'utilisateur.
        """
        if (
            summary is None
            or self._published_repo is None
            or self._qdrant_collection is None
        ):
            return

        if summary.status is not RunStatus.OK:
            logger.warning(
                "Run `%s` : le pointeur de collection n'est PAS mis à jour. Le corpus de "
                "ce run est incomplet, le serving continue de servir le précédent.",
                summary.status.value,
            )
            return

        published = PublishedCollection.of(
            self._qdrant_collection,
            run_id=summary.run_id,
            document_count=summary.stats.counts.get(DOCUMENT_PERSISTED, 0),
        )
        self._runtime.run(self._published_repo.publish(published))
        logger.info(
            "Collection publiée : `%s` (%d documents) — c'est elle que le serving lira.",
            published.collection_name,
            published.document_count,
        )

    def _track_and_close(self, summary: RunSummary | None) -> None:
        """Enregistre le bilan dans le tracker, puis ferme le run — **toujours**.

        Appelé depuis `after_pipeline_run` ET `on_pipeline_error` : quel que soit le
        sort du pipeline, le run d'expérience doit être clos, sinon le suivant se
        grefferait sur un run resté ouvert. `end_run` est en `finally` pour cette
        raison — une exception dans `log_summary` (backend injoignable) ne doit pas
        laisser le run pendant.

        Un `summary` à `None` (agrégateur/dépôts non initialisés) n'a rien à logguer,
        mais le run peut malgré tout avoir été ouvert : on ferme quand même.
        """
        if self._tracker is None:
            return
        try:
            if summary is not None:
                self._tracker.log_summary(summary)
        finally:
            self._tracker.end_run()

    @hook_impl
    def after_pipeline_run(self, run_params: dict[str, Any]) -> None:
        if self._telemetry and self._context:
            self._telemetry.emit(
                build_event(
                    event_type=PIPELINE_RUN_COMPLETED,
                    run_id=self._context.run_id,
                    owner_id=self._context.owner_id,
                    source=self._context.source,
                    payload={
                        "pipeline": run_params.get("pipeline_name", "__default__")
                    },
                )
            )
        # Les chunks que l'embedder a dû raccourcir. Le compteur vit sur l'embedder (il
        # est le seul à voir le refus du service) et il est lu ICI, une fois, en fin de
        # run. Les WRITES pendant le run viennent de plusieurs workers : l'embedder les
        # protège lui-même (verrou + ensemble de chunk_ids). La lecture, elle, est
        # postérieure à tous les workers — et le port `BaseEmbedder` n'a pas à connaître
        # la télémétrie pour un détail qui ne concerne qu'une de ses implémentations.
        self._declare_truncations()

        # Le drain AVANT le bilan, et l'ordre est tout l'enjeu : c'est lui qui révèle
        # les écritures d'audit perdues, et un bilan persisté avant de le savoir ne peut
        # pas en tenir compte. Il déclarerait `ok` un run dont il ne peut plus prouver la
        # complétude — exactement le mensonge qu'on cherche à rendre impossible.
        self._drain_and_declare()

        # Les stats des workers ont déjà été POUSSÉES ici par le node `report` (cf.
        # `absorb`). `_persist_run_summary` dérive le statut de ces compteurs : sans eux,
        # pas un seul document perdu ne serait visible, et le run serait `ok` quoi qu'il
        # arrive.
        summary = self._persist_run_summary(status="ok")

        # Et SEULEMENT si ce bilan dit `ok`, on publie l'empreinte : c'est ce que le
        # serving lira. Un run dégradé ne publie pas — le dernier corpus complet reste
        # en place. La publication est la CONSÉQUENCE du bilan, jamais son présupposé.
        self._publish_collection(summary)

        # Le bilan part aussi vers le tracker (§9), et le run d'expérience se ferme. En
        # `noop` c'est sans effet ; en MLflow, c'est ici que le fingerprint devient un
        # run consultable, paramètres et compteurs en clair.
        self._track_and_close(summary)

        self._runtime.close()

    @hook_impl
    def on_pipeline_error(self, error: Exception, run_params: dict[str, Any]) -> None:
        if self._telemetry and self._context:
            self._telemetry.emit(
                build_event(
                    event_type=PIPELINE_RUN_FAILED,
                    run_id=self._context.run_id,
                    owner_id=self._context.owner_id,
                    source=self._context.source,
                    payload={
                        "pipeline": run_params.get("pipeline_name", "__default__"),
                        "error": str(error),
                    },
                    success=False,
                    error_message=str(error),
                )
            )
        # Les chunks raccourcis se déclarent AUSSI sur un run cassé. Le raccourcissement a
        # bien eu lieu (l'embedder a tourné avant l'échec) et il pointe une config à
        # corriger : le taire parce que le run a cassé plus loin perdrait l'indice. Émis
        # AVANT le drain, comme dans le chemin nominal, pour que l'événement soit vidé.
        self._declare_truncations()

        # Drainer AVANT le bilan, ici aussi : le statut restera `failed` de toute façon
        # (il ne se dérive pas des compteurs), mais le compteur `audit.write.failed`
        # doit figurer dans le bilan — sur un run qui a cassé, savoir si la trace elle
        # aussi est trouée décide de ce qu'on peut conclure du reste.
        self._drain_and_declare()

        # ⚠️ Le bilan sera PAUVRE : les stats des workers ne remontent que par le node
        # `report`, qui est terminal. Un pipeline qui casse avant lui ne persiste que les
        # compteurs du process principal. Le statut `failed` reste vrai — c'est son
        # détail qui manque.
        summary = self._persist_run_summary(status="failed", error_message=str(error))

        # Même sur un run cassé, le run d'expérience doit être clos — un run MLflow
        # laissé ouvert verrait le prochain lancement s'y greffer. Le bilan est pauvre
        # (cf. plus haut), mais son statut `failed` est vrai et mérite d'être tracé.
        self._track_and_close(summary)

        self._runtime.close()


def _build_workflow_config(params: dict[str, Any]) -> WorkflowConfig:
    """``parameters.yml`` → ``WorkflowConfig``. La seule traduction, et elle est ici.

    C'est le point où Kedro cesse d'être la vérité (§9) : le YAML *peuple* la config,
    il ne la *définit* pas. Cette fonction est le seul endroit du dépôt qui connaisse la
    forme du YAML ; ``core/`` n'en sait rien et ne doit rien en savoir.

    Les défauts ne sont pas des valeurs de confort : chacun est une décision qui sera
    hashée. Un défaut qui change en silence change le nom de la collection, donc écrit
    les vecteurs ailleurs — d'où le cliquet ``golden/test_fingerprint.py``.
    """
    workflow = params.get("workflow", {})
    chunking = workflow.get("chunking", {})
    normalization = workflow.get("normalization", {})
    embedding = workflow.get("embedding", {})

    return WorkflowConfig(
        normalization=NormalizationConfig(
            # §4 n'est pas écrite : il n'y a aujourd'hui AUCUNE normalisation
            # typographique. « none » le dit. Le jour où elle atterrit, elle exporte sa
            # version, ce champ la lit, et la collection change toute seule.
            version=normalization.get("version", "none"),
        ),
        chunking=ChunkingConfig(
            strategy=chunking.get("strategy", "legi-structural-v1"),
            size=chunking.get("chunk_size", 128),
            overlap=chunking.get("chunk_overlap", 25),
        ),
        embedding=EmbeddingConfig(
            model_name=embedding.get(
                "embedding_model", "sentence-transformers/all-mpnet-base-v2"
            ),
            dimension=embedding.get("dimension", 768),
        ),
    )


def _resolve_embedding_enabled(params: dict[str, Any], environment: str) -> bool:
    """L'embedding est-il calculé pour ce run ? (ADR-023)

    Deux entrées, et l'environnement PRIME. Le flag YAML ``embedding.enabled`` (défaut
    ``true`` : le comportement historique) n'a d'effet qu'en ``dev`` ; partout ailleurs
    on embarque toujours. C'est la même asymétrie que ``nuke_all`` : couper l'embedding
    est une commodité de développement, et une commodité ne doit jamais pouvoir dégrader
    la prod par simple oubli d'une variable. Un ``parameters.yml`` traîné de dev en prod
    avec ``enabled: false`` produirait sinon une collection vide sans que rien ne lève.

    Le flag vit sous ``embedding_runtime`` (ADR-026 : séparé du bloc ``workflow.embedding``
    qui porte modèle et dimension) et n'entre PAS dans le ``WorkflowConfig`` ni dans le
    hash (§6) : ne pas produire de vecteurs n'invalide aucun vecteur —
    ``_build_workflow_config`` l'ignore, et c'est voulu.
    """
    if environment != "dev":
        return True
    embedding_runtime = params.get("embedding_runtime", {})
    return bool(embedding_runtime.get("enabled", True))


def _resolve_node_hydration(params: dict[str, Any], environment: str) -> NodeHydration:
    """L'hydratation des nœuds Neo4j — arbitrée par l'environnement (ADR-022 §2).

    Hors ``dev``, le nœud est MAIGRE et les toggles YAML sont ignorés — garde-fou dur,
    même asymétrie que ``nuke_all`` et l'interrupteur d'embedding : un
    ``include_path: true`` traîné en prod écrirait les chemins de fichiers du poste
    d'ingestion sur chaque nœud, une info locale sans valeur ailleurs que sur ce poste.

    En dev, tout est ouvert par défaut (Neo4j est l'outil d'inspection de la v0) et le
    YAML peut refermer chaque vanne : ``include_path`` = chemins des FICHIERS source,
    ``include_content`` = texte du document (``_text_content``). Ces toggles ne
    concernent QUE Neo4j — le format de clé des métadonnées, lui, n'est pas un toggle.
    """
    if environment != "dev":
        return NodeHydration()
    neo4j = params.get("exportation", {}).get("neo4j", {})
    return NodeHydration(
        metadata=True,
        include_path=bool(neo4j.get("include_path", True)),
        include_content=bool(neo4j.get("include_content", True)),
    )


def _resolve_sources(
    value: str | SourceName | Iterable[str] | None,
) -> tuple[SourceName, ...]:
    """Les sources demandées, ou une erreur qui dit quoi faire.

    Accepte ce qu'un opérateur écrit réellement en ligne de commande :

    - rien / ``"all"``       → **toutes** les sources ingérables (le défaut)
    - ``"cass"``             → une seule
    - ``"cass,jade"``        → plusieurs (Kedro passe les ``--params`` en chaîne)
    - une liste YAML         → plusieurs, si le paramètre vient d'un fichier de conf

    Un ``--params source=cas`` (faute de frappe) doit échouer **au démarrage**, en nommant
    les sources valides. Sans ça, Kedro partirait sur une source inconnue et le run
    n'ingérerait rien — un échec silencieux qui ressemble à un corpus vide. C'est la même
    raison qui fait qu'on ne *filtre* pas les inconnues d'une liste : ``cass,jade`` avec
    une coquille sur ``jade`` doit se plaindre, pas ingérer CASS en silence.
    """
    if value is None:
        return all_sources()

    if isinstance(value, SourceName):
        return (value,)

    if isinstance(value, str):
        # « all » est le nom explicite du défaut. Il existe pour qu'un `.env` ou un
        # `--params` puisse *demander* le comportement par défaut, plutôt que de devoir
        # énumérer six sources pour dire « toutes ».
        if value.strip().lower() in {"", "all", "*"}:
            return all_sources()
        names: list[str] = [part.strip() for part in value.split(",") if part.strip()]
    else:
        names = [str(part).strip() for part in value]

    if not names:
        return all_sources()

    resolved: list[SourceName] = []
    for name in names:
        try:
            source = SourceName(name.lower())
        except ValueError as exc:
            connues = ", ".join(s.value for s in all_sources())
            msg = f"Source inconnue : {name!r}. Sources ingérables : {connues}."
            raise ValueError(msg) from exc
        if source not in resolved:
            resolved.append(source)

    return tuple(resolved)
