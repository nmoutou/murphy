"""Les sources du run : `kedro run` nu ingère tout, et une coquille arrête le run."""

from __future__ import annotations

import pytest

from ragcore.core.models.enums import SourceName
from ragcore.orchestration.kedro.run_parameters import resolve_sources
from ragcore.sources.registry import all_sources, definition_for


def test_bare_run_ingests_every_source() -> None:
    """Rien de spécifié ⇒ toutes les sources ingérables."""
    assert resolve_sources(None) == all_sources()
    assert len(resolve_sources(None)) == 6


def test_default_derives_from_registry_not_from_the_enum() -> None:
    """Le défaut vient de `SOURCES`, pas de `SourceName` : JORF et UPLOAD n'ont pas de
    connecteur."""
    resolved = set(resolve_sources(None))

    assert SourceName.JORF not in resolved
    assert SourceName.UPLOAD not in resolved
    assert SourceName.LEGI in resolved
    assert SourceName.CONSTIT in resolved


@pytest.mark.parametrize("value", ["all", "*", "", "  "])
def test_all_is_the_explicit_name_of_the_default(value: str) -> None:
    """« all » demande le défaut sans énumérer les sources."""
    assert resolve_sources(value) == all_sources()


def test_single_source_still_works() -> None:
    """Une seule source, pour le rejeu ciblé."""
    assert resolve_sources("cass") == (SourceName.CASS,)


def test_comma_separated_subset() -> None:
    """Kedro passe les `--params` en chaîne : `source=cass,jade`."""
    assert resolve_sources("cass,jade") == (SourceName.CASS, SourceName.JADE)


def test_list_from_yaml_config() -> None:
    """Le même paramètre, en liste depuis un fichier de conf."""
    assert resolve_sources(["cass", "jade"]) == (SourceName.CASS, SourceName.JADE)


def test_order_is_stable() -> None:
    """Ordre reproductible."""
    assert resolve_sources(None) == resolve_sources(None)
    assert resolve_sources("all")[0] is SourceName.LEGI


def test_duplicates_collapse() -> None:
    """`cass,cass` ne lit pas CASS deux fois."""
    assert resolve_sources("cass,cass") == (SourceName.CASS,)


def test_typo_fails_loudly_and_names_the_valid_sources() -> None:
    """Une coquille échoue au démarrage, en nommant les sources valides : sinon le run
    n'ingérerait rien, comme un corpus vide."""
    with pytest.raises(ValueError, match="Source inconnue : 'cas'"):
        resolve_sources("cas")

    with pytest.raises(ValueError, match="legi"):
        resolve_sources("cas")


def test_a_typo_inside_a_list_does_not_silently_ingest_the_rest() -> None:
    """`cass,jde` se plaint au lieu d'ingérer CASS seule en silence."""
    with pytest.raises(ValueError, match="Source inconnue : 'jde'"):
        resolve_sources("cass,jde")


def test_a_source_without_connector_is_refused() -> None:
    """JORF, sans connecteur, lève."""
    with pytest.raises(ValueError, match="Source non ingérable"):
        definition_for(SourceName.JORF)
