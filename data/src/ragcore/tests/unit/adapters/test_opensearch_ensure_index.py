"""La dimension des vecteurs à la création de l'index, et le garde-fou sur un index
existant. Contre un vrai OpenSearch : en intégration."""

from typing import Any, cast

import pytest
from opensearchpy import AsyncOpenSearch

from ragcore.adapters.storage.opensearch.search_index import (
    OpenSearchSearchIndex,
    _index_definition,
)

INDEX = "documents_test"
MEASURED = 1024
LEGACY = 768


class _FakeIndices:
    def __init__(self, existing_mappings: dict[str, Any] | None) -> None:
        self._existing_mappings = existing_mappings
        self.created: dict[str, Any] | None = None

    async def exists(self, index: str) -> bool:
        return self._existing_mappings is not None

    async def create(self, index: str, body: dict[str, Any]) -> None:
        self.created = body

    async def get_mapping(self, index: str) -> dict[str, Any]:
        return {index: {"mappings": self._existing_mappings}}


class _FakeClient:
    def __init__(self, indices: _FakeIndices) -> None:
        self.indices = indices


def _search_index(indices: _FakeIndices) -> OpenSearchSearchIndex:
    client = cast(AsyncOpenSearch, _FakeClient(indices))
    return OpenSearchSearchIndex(client, INDEX, MEASURED)


def _vector_dimensions(mappings: dict[str, Any]) -> list[int]:
    properties = mappings["properties"]
    return [
        properties["title_embedding"]["dimension"],
        properties["passages"]["properties"]["embedding"]["dimension"],
    ]


async def test_un_index_absent_est_cree_a_la_dimension_MESUREE() -> None:
    indices = _FakeIndices(existing_mappings=None)

    await _search_index(indices).ensure_index()

    assert indices.created is not None
    assert _vector_dimensions(indices.created["mappings"]) == [MEASURED, MEASURED]


async def test_un_index_existant_de_meme_dimension_est_garde_tel_quel() -> None:
    indices = _FakeIndices(_index_definition(MEASURED)["mappings"])

    await _search_index(indices).ensure_index()

    assert indices.created is None


async def test_un_index_existant_dune_autre_dimension_ARRETE_le_run() -> None:
    """Sinon OpenSearch rejetterait chaque document, un par un."""
    indices = _FakeIndices(_index_definition(LEGACY)["mappings"])

    with pytest.raises(
        ValueError, match=f"dimension {LEGACY}, .* en produit {MEASURED}"
    ):
        await _search_index(indices).ensure_index()
    assert indices.created is None
