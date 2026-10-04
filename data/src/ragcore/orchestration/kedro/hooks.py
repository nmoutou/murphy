"""Le cycle de vie du run : le hook ouvre une ``RunSession`` en tête de run et la clôt
en fin."""

from __future__ import annotations

import logging
from pathlib import Path

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog

from ragcore.adapters.config.settings import (
    InfraSettings,
    get_chunking_config,
    get_embedding_runtime_settings,
    get_infra_settings,
    get_log_level,
)
from ragcore.adapters.runtime import AsyncioRuntime, AsyncioRuntimeFactory
from ragcore.application.resolve_relations import ResolveRelationsService
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.enums import SourceName
from ragcore.core.models.run_summary import RunStatus
from ragcore.core.ports.embedder import BaseEmbedder
from ragcore.orchestration.kedro.assembly import (
    build_processing_stack,
    build_runner,
    prepare_embedder,
)
from ragcore.orchestration.kedro.logging_levels import apply_log_level
from ragcore.orchestration.kedro.run_parameters import load_parameters
from ragcore.orchestration.kedro.run_plan import RunPlan, plan_run
from ragcore.orchestration.kedro.run_session import RunSession, start_telemetry
from ragcore.orchestration.kedro.stores import (
    MetaStores,
    close_clients,
    ensure_indexes,
    open_clients,
    open_document_stores,
    open_meta_stores,
)

logger = logging.getLogger(__name__)


class TelemetryHooks:
    def __init__(self) -> None:
        self._runtime_instance: AsyncioRuntime | None = None
        self._session: RunSession | None = None
        """Absente tant que l'assemblage n'a pas abouti."""

    @property
    def _runtime(self) -> AsyncioRuntime:
        """Construit au premier usage, jamais dans `__init__` : Kedro `deepcopy` les
        hooks à l'ouverture de session, et une boucle asyncio n'est pas copiable
        (`cannot pickle '_contextvars.Context'`).
        """
        if self._runtime_instance is None:
            self._runtime_instance = AsyncioRuntimeFactory().build(worker_id=-1)
        return self._runtime_instance

    @hook_impl
    def before_pipeline_run(self, catalog: DataCatalog) -> None:
        """Assemble le run et le pose au catalogue."""
        apply_log_level(get_log_level())
        settings = get_infra_settings()
        plan = plan_run(load_parameters(catalog), settings, get_chunking_config())
        embedder = prepare_embedder(get_embedding_runtime_settings(), self._runtime)
        for name, value in self._assemble(settings, plan, embedder).items():
            catalog.save(name, value)

    def _assemble(
        self, settings: InfraSettings, plan: RunPlan, embedder: BaseEmbedder
    ) -> dict[str, object]:
        """Les dépôts du hook, sur sa boucle, servent les nœuds non parallélisés. Les
        workers de la phase 1 fabriquent les leurs : un client est lié à la boucle qui
        l'a touché en premier.
        """
        clients = open_clients(settings)
        self._runtime.defer_close(lambda: close_clients(clients))
        ensure_indexes(clients, settings, self._runtime)
        stores = open_document_stores(clients, settings, plan)
        meta = open_meta_stores(clients, settings)
        session = self._open_session(plan.sources, meta, embedder)
        stack = build_processing_stack(plan, Path(settings.xml_source_path), embedder)
        return {
            "connector": stack.connector,
            "parser": stack.parser,
            "doc_repo": stores.documents,
            "graph_repo": stores.graph,
            "search_index": stores.search_index,
            "runner": build_runner(settings, plan, session.context, stack),
            "resolve_service": ResolveRelationsService(
                graph_repo=stores.graph,
                pending_repo=stores.pending,
                telemetry=session.telemetry,
            ),
            "pipeline_context": session.context,
            "telemetry": session.telemetry,
            # `report` y pousse les stats des workers, que le hook ne peut pas relire
            "run_stats_sink": session.aggregator,
            "pipeline_runtime": self._runtime,
            "skip_unconfigured": plan.skip_unconfigured,
            "nuke_all": plan.nuke_all,
        }

    def _open_session(
        self,
        sources: tuple[SourceName, ...],
        meta: MetaStores,
        embedder: BaseEmbedder,
    ) -> RunSession:
        context = PipelineContext.create(sources=sources)
        telemetry, aggregator = start_telemetry(context)
        self._session = RunSession(
            context=context,
            telemetry=telemetry,
            aggregator=aggregator,
            summaries=meta.summaries,
            embedder=embedder,
            runtime=self._runtime,
        )
        return self._session

    @hook_impl
    def after_pipeline_run(self) -> None:
        if self._session is not None:
            self._session.close(RunStatus.OK)
        self._close_runtime()

    @hook_impl
    def on_pipeline_error(self, error: Exception) -> None:
        if self._session is not None:
            # Bilan pauvre : les stats des workers ne remontent que par `report`
            self._session.close(RunStatus.FAILED, error_message=str(error))
        self._close_runtime()

    def _close_runtime(self) -> None:
        """Si elle a jamais été ouverte."""
        if self._runtime_instance is not None:
            self._runtime_instance.close()
