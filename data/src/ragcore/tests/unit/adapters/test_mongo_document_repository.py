"""Ce que le dépôt Mongo écrit d'un document : ``source_files`` seulement en dev, sa
longueur et les titres de son texte parent."""

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from ragcore.adapters.storage.mongo.client import MongoClient
from ragcore.adapters.storage.mongo.document_repository import MongoDocumentRepository
from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.enums import DocumentType, SourceName
from ragcore.core.models.identifiers import Identifier

DB_NAME = "MURPHY_DATA"
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


DECREE = "Décret n° 2004-374 du 29 avril 2004"


def _document(
    content: str = "contenu", context: list[dict[str, str]] | None = None
) -> ParsedDocument:
    structure: dict[str, Any] = {"sections": []}
    if context is not None:
        structure["context"] = context
    return ParsedDocument(
        identifier=Identifier(raw="LEGIARTI000000000001"),
        source=SourceName.LEGI,
        document_type=DocumentType.ARTICLE,
        title="Article 1",
        content=content,
        structure=structure,
        metadata={},
        parsed_at=datetime.now(UTC),
        source_files=SOURCE_FILES,
    )


def _write(
    include_path: bool = False, document: ParsedDocument | None = None
) -> dict[str, Any]:
    collection = _RecordingCollection()
    client = cast(MongoClient, {DB_NAME: {COLLECTION: collection}})
    repository = MongoDocumentRepository(client, DB_NAME, include_path=include_path)
    asyncio.run(repository.upsert(document or _document()))
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
    """ADR-011 : ``structure`` est redondante avec Neo4j et les chunks."""
    assert "structure" not in _write(include_path)


def test_la_longueur_compte_des_points_de_code() -> None:
    """« é » et « 📜 » comptent un chacun, comme dans le budget du serving."""
    written = _write(document=_document(content="Arrêté 📜"))

    assert written["content_length"] == len("Arrêté 📜") == 8


def test_les_titres_du_texte_parent_sont_ecrits() -> None:
    context = [
        {"kind": "TITRE_TXT", "label": DECREE},
        {"kind": "TITRE_TM", "label": "Chapitre Ier"},
        {"kind": "TITRE_TXT", "label": DECREE},
    ]

    written = _write(document=_document(context=context))

    assert written["parent_text_title"] == [DECREE]


def test_sans_texte_parent_le_champ_est_absent() -> None:
    assert "parent_text_title" not in _write()
