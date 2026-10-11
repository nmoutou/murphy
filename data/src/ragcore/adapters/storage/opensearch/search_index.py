"""Implémentation OpenSearch du SearchIndexRepository."""

import json
from importlib import resources
from typing import Any

from opensearchpy import AsyncOpenSearch

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.search_content import SearchContent

from .index_document import build_index_document

__all__ = ["OpenSearchSearchIndex"]

_INDEX_DEFINITION_FILE = "index_definition.json"
# Ni exception ni log : un absent n'est pas une erreur pour une suppression
_NOT_FOUND = 404
# `null` rend au réglage sa valeur par défaut
_SUSPENDED_REFRESH = {"index": {"refresh_interval": "-1"}}
_DEFAULT_REFRESH = {"index": {"refresh_interval": None}}
# La fusion réécrit tout l'index : le timeout par requête du client (10 s) n'y suffit pas
_FORCE_MERGE_TIMEOUT_S = 1800


def _load_index_definition() -> dict[str, Any]:
    definition = resources.files(__package__).joinpath(_INDEX_DEFINITION_FILE)
    loaded: dict[str, Any] = json.loads(definition.read_text(encoding="utf-8"))
    return loaded


def _vector_fields(properties: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return (
        properties["title_embedding"],
        properties["passages"]["properties"]["embedding"],
    )


def _index_definition(vector_dimension: int) -> dict[str, Any]:
    """Le fichier ne porte pas la dimension : elle est celle que mesure TEI."""
    definition = _load_index_definition()
    for field in _vector_fields(definition["mappings"]["properties"]):
        field["dimension"] = vector_dimension
    return definition


class OpenSearchSearchIndex:
    def __init__(
        self, client: AsyncOpenSearch, index_name: str, vector_dimension: int
    ) -> None:
        self._client = client
        self._index_name = index_name
        self._vector_dimension = vector_dimension

    async def index_document(
        self, parsed: ParsedDocument, content: SearchContent
    ) -> None:
        """Un seul `PUT` : le document est remplacé entier, passages compris, sans
        fenêtre où il manquerait."""
        await self._client.index(
            index=self._index_name,
            id=parsed.identifier.serialize(),
            body=build_index_document(parsed, content),
        )

    async def delete_document(self, identifier: Identifier) -> None:
        await self._client.delete(
            index=self._index_name, id=identifier.serialize(), ignore=_NOT_FOUND
        )

    async def ensure_index(self) -> None:
        """À appeler une seule fois, avant le pool : depuis les workers, ce
        check-then-act ferait échouer tous les créateurs sauf un."""
        if await self._client.indices.exists(index=self._index_name):
            await self._check_vector_dimension()
            return
        await self._client.indices.create(
            index=self._index_name, body=_index_definition(self._vector_dimension)
        )

    async def _check_vector_dimension(self) -> None:
        """Un index existant n'est jamais modifié : d'une autre dimension, il ferait
        rejeter chaque document, un par un."""
        response = await self._client.indices.get_mapping(index=self._index_name)
        properties = next(iter(response.values()))["mappings"]["properties"]
        indexed = {field["dimension"] for field in _vector_fields(properties)}
        if indexed != {self._vector_dimension}:
            raise ValueError(
                f"L'index « {self._index_name} » a des vecteurs de dimension "
                f"{', '.join(map(str, sorted(indexed)))}, or le modèle d'embedding en "
                f"produit {self._vector_dimension}. Changer de modèle impose de supprimer "
                f"l'index et de réingérer tout le corpus (`nuke_all: true` en dev)."
            )

    async def drop_index(self) -> None:
        """Irréversible. Seulement l'index du run : les index système (Dashboards,
        plugins) vivent dans le même cluster."""
        await self._client.indices.delete(index=self._index_name, ignore=_NOT_FOUND)

    async def suspend_refresh(self) -> None:
        await self._client.indices.put_settings(
            index=self._index_name, body=_SUSPENDED_REFRESH
        )

    async def resume_refresh(self) -> None:
        await self._client.indices.refresh(index=self._index_name)
        await self._client.indices.put_settings(
            index=self._index_name, body=_DEFAULT_REFRESH
        )

    async def force_merge(self) -> None:
        """Un seul segment, donc un seul graphe HNSW à parcourir par requête kNN : l'index
        n'est plus écrit avant le run suivant. Le graphe reconstruit est approché, et
        peut décaler un peu les rangs vectoriels. Le refresh publie le segment fusionné :
        un shard inactif ne se rafraîchit pas seul."""
        await self._client.indices.forcemerge(
            index=self._index_name,
            max_num_segments=1,
            request_timeout=_FORCE_MERGE_TIMEOUT_S,
        )
        await self._client.indices.refresh(index=self._index_name)
