"""Ce que le dépôt Mongo écrit d'un document : ``source_files`` seulement en dev."""

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import Identifier

DB_NAME = "LEGIFRANCE"
COLLECTION = "documents"
SOURCE_FILES = ("/corpus/LEGI/article.xml",)


class _RecordingCollection:
    """Garde le dernier document passé à ``replace_one``."""

    def __init__(self) -> None:
        self.written: dict[str, Any] = {}

    async def replace_one(
        self, filter_: dict[str, Any], document: dict[str, Any], upsert: bool
    ) -> None:
        self.written = document


def _document() -> ParsedDocument:
    return ParsedDocument(
        identifier=Identifier(raw="LEGIARTI000000000001"),
        source=SourceName.LEGI,
        title="Article 1",
        content="contenu",
        structure={"sections": []},
        metadata={},
        parsed_at=datetime.now(UTC),
        source_files=SOURCE_FILES,
    )


def _write(include_path: bool) -> dict[str, Any]:
    collection = _RecordingCollection()
    client = cast(MongoClient, {DB_NAME: {COLLECTION: collection}})
    repository = MongoDocumentRepository(client, DB_NAME, include_path=include_path)
    asyncio.run(repository.upsert(_document()))
    return collection.written


def test_par_defaut_les_chemins_ne_sont_pas_ecrits() -> None:
    collection = _RecordingCollection()
    client = cast(MongoClient, {DB_NAME: {COLLECTION: collection}})
    asyncio.run(MongoDocumentRepository(client, DB_NAME).upsert(_document()))

    assert "source_files" not in collection.written


def test_avec_include_path_les_chemins_sont_ecrits() -> None:
    assert _write(include_path=True)["source_files"] == list(SOURCE_FILES)


@pytest.mark.parametrize("include_path", [True, False])
def test_la_structure_n_est_jamais_ecrite(include_path: bool) -> None:
    """ADR-022 §4 : ``structure`` est redondante avec Neo4j et les chunks."""
    assert "structure" not in _write(include_path)
