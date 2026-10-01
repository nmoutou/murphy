"""Le contexte porte toutes les sources du run ; un événement, une seule ou aucune."""

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.enums import SourceName


def test_a_single_source_run_stamps_its_source() -> None:
    context = PipelineContext.create(sources=(SourceName.CASS,))

    assert context.source is SourceName.CASS


def test_a_multi_source_run_stamps_none() -> None:
    """Les événements de document portent la source de leur document : le contexte
    n'en invente pas une pour le run entier."""
    context = PipelineContext.create(sources=(SourceName.CASS, SourceName.JADE))

    assert context.sources == (SourceName.CASS, SourceName.JADE)
    assert context.source is None
