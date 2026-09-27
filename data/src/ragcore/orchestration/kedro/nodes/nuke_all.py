from __future__ import annotations

import logging
from typing import Any

from ragcore.adapters.config.settings import get_infra_settings
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.adapters.storage.mongo.manifest_repository import MongoManifestRepository
from ragcore.adapters.storage.mongo.schemas import ensure_data_indexes
from ragcore.adapters.storage.neo4j.graph_repository import Neo4jGraphRepository
from ragcore.adapters.storage.qdrant.vector_repository import QdrantVectorRepository
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import MAINTENANCE_NUKE_ALL_EXECUTED

logger = logging.getLogger(__name__)


class NukeAllOutsideDevError(RuntimeError):
    """Le mode ``nuke_all`` a été demandé hors d'un environnement `dev`.

    Ce n'est pas un avertissement : c'est un arrêt. Effacer TOUTES les données de
    TOUTES les bases n'a de sens qu'en développement, où les données sont jetables.
    Ailleurs, l'intention est presque sûrement une erreur — et le mode de défaillance
    d'un `nuke` mal placé est irréversible. On lève avant de toucher la moindre base.
    """


def nuke_all_node(
    doc_repo: MongoDocumentRepository,
    manifest_repo: MongoManifestRepository,
    graph_repo: Neo4jGraphRepository,
    vector_repo: QdrantVectorRepository,
    maintenance_params: dict[str, Any],
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
    pipeline_runtime: AsyncRuntime,
) -> dict[str, bool]:
    """Efface TOUTES les données de TOUTES les bases quand ``nuke_all=true``.

    Tourne en tête d'ingestion. C'est le levier disque du développement : les données
    n'ont aucune valeur en v0, et ``force_drop`` par store était trop chirurgical pour
    récupérer la place que prenaient les collections Qdrant d'anciennes stratégies.

    Ce que le nuke efface — et ce qu'il PRÉSERVE :
    - Mongo *données* : collections `documents` + `manifest` (base `LEGIFRANCE`).
    - Neo4j : le graphe entier.
    - Qdrant : **toutes** les collections du store, pas seulement celle du fingerprint
      courant — c'est là que se cache la place perdue.
    - **PRÉSERVÉ : la base méta Mongo** (`MURPHY_META` : audit, bilans de run,
      pendantes). Un nuke ne doit jamais emporter la mémoire de ce qu'on a fait —
      c'est elle qui rend un run *invérifiable* si elle disparaît, pas le corpus.
    """
    if not maintenance_params.get("nuke_all"):
        # Setup partagé quand même : la collection doit exister avant le pool de
        # workers, qu'on ait nuké ou démarré à froid. La laisser aux workers les met
        # en course, et Qdrant répond `409` à tous sauf un — un document perdu par
        # worker perdant.
        pipeline_runtime.run(vector_repo.ensure_collection())
        return {"mongodb": False, "neo4j": False, "qdrant": False}

    _assert_dev_environment()
    logger.warning(
        "nuke_all activé (ENVIRONMENT=dev) : effacement de TOUTES les données de TOUTES les bases"
    )
    _drop_mongo(doc_repo, manifest_repo, pipeline_runtime)

    logger.warning("nuke_all Neo4j : suppression complète du graphe")
    pipeline_runtime.run(graph_repo.drop_all())

    logger.warning("nuke_all Qdrant : suppression de TOUTES les collections du store")
    pipeline_runtime.run(vector_repo.drop_all_collections())

    dropped: dict[str, bool] = {"mongodb": True, "neo4j": True, "qdrant": True}

    # Setup partagé, hors du drop : la collection du fingerprint courant doit exister
    # avant que le pool ne démarre, qu'on vienne de tout dropper ou non.
    pipeline_runtime.run(vector_repo.ensure_collection())

    _emit_nuked(telemetry, pipeline_context, dropped)
    return dropped


def _emit_nuked(
    telemetry: TelemetryPort, context: PipelineContext, dropped: dict[str, bool]
) -> None:
    telemetry.emit(
        build_event(
            event_type=MAINTENANCE_NUKE_ALL_EXECUTED,
            run_id=context.run_id,
            owner_id=context.owner_id,
            source=context.source,
            payload=dropped,
        )
    )


def _assert_dev_environment() -> None:
    """Le garde-fou, AVANT toute écriture. L'absence de `ENVIRONMENT` vaut `prod` (voir
    InfraSettings.environment) : un `.env` incomplet est traité comme protégé."""
    environment = get_infra_settings().environment
    if environment != "dev":
        raise NukeAllOutsideDevError(
            f"nuke_all refusé : ENVIRONMENT={environment!r}, attendu 'dev'. "
            f"Ce mode efface TOUTES les données de TOUTES les bases — il n'est autorisé "
            f"que là où les données sont jetables. Pour l'exécuter, ENVIRONMENT doit "
            f"valoir strictement 'dev' dans le .env de la racine."
        )


def _drop_mongo(
    doc_repo: MongoDocumentRepository,
    manifest_repo: MongoManifestRepository,
    pipeline_runtime: AsyncRuntime,
) -> None:
    logger.warning("nuke_all Mongo : suppression des collections documents + manifest")
    pipeline_runtime.run(doc_repo.drop_collection())
    pipeline_runtime.run(manifest_repo.drop_collection())
    # Dropper une collection détruit ses index avec elle. Ceux que le hook a posés en
    # `before_pipeline_run` viennent de disparaître : sans ce rappel, tout le run
    # réécrit dans des collections nues, et l'unicité de (identifier, owner_id) ne
    # protège plus rien — en silence.
    pipeline_runtime.run(ensure_data_indexes(doc_repo.database))
