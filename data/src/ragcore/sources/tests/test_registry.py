"""Les labels Neo4j déclarés par les sources, fusionnés en une table."""

import pytest

from ragcore.core.models.enums import SourceName
from ragcore.sources.legi.table import LEGI_ROLE_TABLE
from ragcore.sources.registry import SourceDefinition, node_labels_by_prefix


def _definition(node_labels: dict[str, str]) -> SourceDefinition:
    return SourceDefinition(
        connector=lambda root: root,
        table=LEGI_ROLE_TABLE,
        subdirectory="X",
        node_labels=node_labels,
    )


def test_les_labels_de_toutes_les_sources_sont_fusionnes() -> None:
    assert node_labels_by_prefix() == {
        "LEGIARTI": "Article",
        "LEGITEXT": "Texte",
        "LEGISCTA": "Section",
    }


def test_un_meme_label_declare_par_deux_sources_passe() -> None:
    sources = {
        SourceName.CASS: _definition({"JURITEXT": "Decision"}),
        SourceName.CAPP: _definition({"JURITEXT": "Decision"}),
    }

    assert node_labels_by_prefix(sources) == {"JURITEXT": "Decision"}


def test_deux_labels_pour_un_meme_prefixe_levent() -> None:
    sources = {
        SourceName.CASS: _definition({"JURITEXT": "Decision"}),
        SourceName.CAPP: _definition({"JURITEXT": "Arret"}),
    }

    with pytest.raises(ValueError, match="JURITEXT"):
        node_labels_by_prefix(sources)
