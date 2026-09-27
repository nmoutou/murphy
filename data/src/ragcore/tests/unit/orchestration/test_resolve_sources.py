"""Le DÉFAUT du pipeline : `kedro run` nu ingère TOUT.

Ce fichier verrouille le changement de comportement. Le défaut est la seule chose qu'un
opérateur n'écrit jamais explicitement — donc la seule qu'un test doit tenir, parce que
personne ne la relira dans une ligne de commande.
"""

from __future__ import annotations

import pytest

from ragcore.core.models.enums import SourceName
from ragcore.orchestration.kedro.run_parameters import resolve_sources
from ragcore.sources.registry import all_sources, definition_for


def test_bare_run_ingests_every_source() -> None:
    """LE test de ce lot. Rien de spécifié ⇒ toutes les sources ingérables.

    Le défaut historique était `legi` : un `kedro run` nu laissait cinq bases sur six
    intactes, sans le dire, et se terminait « ok ».
    """
    assert resolve_sources(None) == all_sources()
    assert len(resolve_sources(None)) == 6


def test_default_derives_from_registry_not_from_the_enum() -> None:
    """`SourceName` déclare le vocabulaire ; `SOURCES` déclare ce qui est INGÉRABLE.

    JORF et UPLOAD existent dans l'enum sans connecteur. Un défaut dérivé de l'enum
    ferait planter le run nu sur JORF — et le referait planter à chaque *ajout* de
    vocabulaire, punissant le geste qu'on veut rendre anodin.
    """
    resolved = set(resolve_sources(None))

    assert SourceName.JORF not in resolved
    assert SourceName.UPLOAD not in resolved
    assert SourceName.LEGI in resolved
    assert SourceName.CONSTIT in resolved


@pytest.mark.parametrize("value", ["all", "*", "", "  "])
def test_all_is_the_explicit_name_of_the_default(value: str) -> None:
    """« all » permet de DEMANDER le défaut sans énumérer six sources."""
    assert resolve_sources(value) == all_sources()


def test_single_source_still_works() -> None:
    """La restriction reste ouverte — c'est elle qui rend le rejeu ciblé possible."""
    assert resolve_sources("cass") == (SourceName.CASS,)


def test_comma_separated_subset() -> None:
    """Kedro passe les `--params` en chaîne : `source=cass,jade` doit marcher."""
    assert resolve_sources("cass,jade") == (SourceName.CASS, SourceName.JADE)


def test_list_from_yaml_config() -> None:
    """Le même paramètre peut venir d'un fichier de conf, en liste."""
    assert resolve_sources(["cass", "jade"]) == (SourceName.CASS, SourceName.JADE)


def test_order_is_stable() -> None:
    """Un run doit être reproductible jusque dans l'ordre où il lit ses sources."""
    assert resolve_sources(None) == resolve_sources(None)
    assert resolve_sources("all")[0] is SourceName.LEGI


def test_duplicates_collapse() -> None:
    """`cass,cass` ne lit pas CASS deux fois — ce serait ingérer en double."""
    assert resolve_sources("cass,cass") == (SourceName.CASS,)


def test_typo_fails_loudly_and_names_the_valid_sources() -> None:
    """Une coquille échoue AU DÉMARRAGE, en contenant sa propre réponse.

    Sans ça, Kedro partirait sur une source inconnue et n'ingérerait rien — un échec
    silencieux qui ressemble trait pour trait à un corpus vide.
    """
    with pytest.raises(ValueError, match="Source inconnue : 'cas'"):
        resolve_sources("cas")

    with pytest.raises(ValueError, match="legi"):
        resolve_sources("cas")


def test_a_typo_inside_a_list_does_not_silently_ingest_the_rest() -> None:
    """`cass,jde` doit se PLAINDRE, pas ingérer CASS en silence.

    Filtrer les inconnues d'une liste rendrait un run partiel indiscernable d'un run
    complet — la faute de frappe deviendrait invisible.
    """
    with pytest.raises(ValueError, match="Source inconnue : 'jde'"):
        resolve_sources("cass,jde")


def test_a_source_without_connector_is_refused() -> None:
    """JORF est dans l'enum mais n'a pas de connecteur : le demander doit lever."""
    with pytest.raises(ValueError, match="Source non ingérable"):
        definition_for(SourceName.JORF)
