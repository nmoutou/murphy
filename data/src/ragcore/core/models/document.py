from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from .enums import DocumentType, SourceName
from .identifiers import Identifier


class RawDocument(BaseModel):
    """Document tel que récupéré par le connector, avant parsing."""

    model_config = ConfigDict(frozen=True)

    source: SourceName
    source_document_id: str
    payload: dict[str, Any]
    fetched_at: datetime


class ParsedDocument(BaseModel):
    """Document parsé, prêt pour le chunking.

    ``identifier`` est sa seule clé en aval (Mongo, OpenSearch, nœud Neo4j). Pas de hash de
    contenu : chaque run réécrit le document en place.
    """

    model_config = ConfigDict(frozen=True)

    identifier: Identifier
    source: SourceName
    document_type: DocumentType
    nature: str | None = None
    """La nature juridique (``LOI``, ``ARRET``, ``QPC``…), en majuscules. ``None`` si la
    source ne la donne pas ou si elle n'apporte rien (``Texte`` dans JADE)."""

    title: str
    content: str
    structure: dict[str, Any]
    metadata: dict[str, Any]

    source_files: tuple[str, ...] = ()
    """Les fichiers XML d'origine (un article LEGI = jusqu'à 2 facettes).

    Écrits dans Mongo et sur le nœud Neo4j seulement avec ``include_path`` : un chemin
    absolu du poste d'ingestion n'a de sens que sur ce poste.
    """
