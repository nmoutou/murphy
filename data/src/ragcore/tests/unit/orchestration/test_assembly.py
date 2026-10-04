"""L'assemblage du run, sans base ni réseau : aucun client ne se connecte à sa
construction, et la vérification du modèle est remplacée.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest

from ragcore.adapters.config.settings import (
    EmbeddingRuntimeSettings,
    InfraSettings,
)
from ragcore.adapters.embedding.tei_embedder import TeiEmbedder
from ragcore.application.ingestion_runner import IngestionRunner
from ragcore.application.run_context import PipelineContext
from ragcore.core.models.processing import ChunkingConfig, EmbeddingModel
from ragcore.orchestration.kedro import assembly
from ragcore.orchestration.kedro.assembly import (
    ReportsTruncations,
    build_processing_stack,
    build_runner,
    prepare_embedder,
)
from ragcore.orchestration.kedro.run_plan import RunPlan, plan_run
from ragcore.orchestration.kedro.stores import (
    InfraClients,
    open_clients,
    open_document_stores,
    open_meta_stores,
)
from ragcore.tests.fakes.embedder import NoopEmbedder
from ragcore.tests.fakes.runtime import FakeRuntime


@pytest.fixture
def settings(tmp_path: Path) -> InfraSettings:
    return InfraSettings(
        source="all",
        environment="prod",
        mongodb_uri="mongodb://localhost:1",
        neo4j_uri="bolt://localhost:1",
        opensearch_url="http://localhost:1",
        opensearch_index="documents",
        xml_source_path=tmp_path,
    )


@pytest.fixture
def plan(settings: InfraSettings) -> RunPlan:
    params = {
        "nuke_all": False,
        "embedding_enabled": True,
        "skip_unconfigured": False,
        "include_path": True,
        "include_content_neo4j": True,
        "source": "cass",
    }
    chunking = ChunkingConfig(max_chars=384, overlap_chars=25)
    return plan_run(params, settings, chunking)


@pytest.fixture
def runtime() -> Iterator[FakeRuntime]:
    fake = FakeRuntime(worker_id=0)
    yield fake
    fake.close()


def _close(clients: InfraClients) -> None:
    clients.mongo.close()
    asyncio.run(clients.neo4j.close())
    asyncio.run(clients.opensearch.close())


def _embedding_settings() -> EmbeddingRuntimeSettings:
    return EmbeddingRuntimeSettings(model="un-modele", service_url="http://localhost:1")


# ── Les clients : le code est partagé, pas les instances ────────────────────────────


def test_chaque_appel_ouvre_des_clients_NEUFS(settings: InfraSettings) -> None:
    """Un worker qui réutiliserait les clients du hook serait lié à la boucle du hook."""
    first, second = open_clients(settings), open_clients(settings)
    try:
        assert first.mongo is not second.mongo
        assert first.neo4j is not second.neo4j
        assert first.opensearch is not second.opensearch
    finally:
        _close(first)
        _close(second)


def test_les_depots_s_ouvrent_sans_se_connecter(
    settings: InfraSettings, plan: RunPlan
) -> None:
    clients = open_clients(settings)
    try:
        open_document_stores(clients, settings, plan)
        open_meta_stores(clients, settings)
    finally:
        _close(clients)


# ── L'embedder : TEI, vérifié et mesuré avant d'être construit ─────────────────────


def test_prepare_embedder_verifie_le_modele_et_mesure_la_dimension(
    runtime: FakeRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    inspected: list[tuple[str, str]] = []

    async def _fake_inspect(base_url: str, expected_model: str) -> EmbeddingModel:
        inspected.append((base_url, expected_model))
        return EmbeddingModel(model_name=expected_model, dimension=768)

    monkeypatch.setattr(assembly, "inspect_served_model", _fake_inspect)

    embedder = prepare_embedder(_embedding_settings(), runtime)

    assert inspected == [("http://localhost:1", "un-modele")]
    assert isinstance(embedder, TeiEmbedder)
    assert embedder.dimension == 768
    assert isinstance(embedder, ReportsTruncations)


def test_prepare_embedder_refuse_un_modele_dune_autre_dimension_que_lindex(
    runtime: FakeRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_inspect(base_url: str, expected_model: str) -> EmbeddingModel:
        return EmbeddingModel(model_name=expected_model, dimension=384)

    monkeypatch.setattr(assembly, "inspect_served_model", _fake_inspect)

    with pytest.raises(ValueError, match="dimension 384"):
        prepare_embedder(_embedding_settings(), runtime)


# ── Le pool ────────────────────────────────────────────────────────


def test_le_pool_s_assemble_sans_ouvrir_de_client(
    plan: RunPlan, settings: InfraSettings
) -> None:
    stack = build_processing_stack(
        plan, settings.xml_source_path, NoopEmbedder(dimension=768)
    )
    context = PipelineContext.create()

    assert isinstance(build_runner(settings, plan, context, stack), IngestionRunner)
