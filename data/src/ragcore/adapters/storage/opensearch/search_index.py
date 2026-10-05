"""Implémentation OpenSearch du SearchIndexRepository."""

import json
from importlib import resources
from typing import Any

from opensearchpy import AsyncOpenSearch

from ragcore.core.models.document import ParsedDocument
from ragcore.core.models.identifiers import Identifier
from ragcore.core.models.search_content import SearchContent

from .index_document import build_index_document

__all__ = ["OpenSearchSearchIndex", "check_vector_dimension"]

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


def check_vector_dimension(dimension: int) -> None:
    """Le mapping fixe la dimension : un modèle d'une autre dimension ferait rejeter
    chaque document, un par un. Vérifié avant le run."""
    mapping = _load_index_definition()["mappings"]["properties"]
    declared = mapping["passages"]["properties"]["embedding"]["dimension"]
    if dimension != declared:
        raise ValueError(
            f"Le modèle d'embedding produit des vecteurs de dimension {dimension}, or "
            f"le mapping de l'index en déclare {declared} ({_INDEX_DEFINITION_FILE}). "
            f"Changer de modèle impose de modifier le mapping et de réingérer tout le "
            f"corpus."
        )


class OpenSearchSearchIndex:
    def __init__(self, client: AsyncOpenSearch, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

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
        if not await self._client.indices.exists(index=self._index_name):
            await self._client.indices.create(
                index=self._index_name, body=_load_index_definition()
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
