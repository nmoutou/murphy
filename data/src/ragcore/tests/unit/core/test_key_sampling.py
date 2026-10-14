"""L'échantillon d'un run partiel : exact, reproductible, emboîté (ADR-034 §9)."""

import pytest

from ragcore.core.services.key_sampling import select_keys

KEYS = [f"LEGIARTI{n:012d}" for n in range(1000)]


@pytest.mark.parametrize(
    ("ratio", "expected"), [(0.1, 100), (0.7, 700), (0.001, 1), (0.0015, 2), (1, 1000)]
)
def test_the_sample_is_exactly_the_ceiling(ratio: float, expected: int) -> None:
    """0,7 × 1000 vaut 700, pas le plafond de 700,0000000000001."""
    assert len(select_keys(KEYS, ratio)) == expected


def test_a_single_key_source_keeps_its_key() -> None:
    assert select_keys(["LEGITEXT000000000001"], 0.01) == {"LEGITEXT000000000001"}


def test_the_sample_does_not_depend_on_the_order_of_the_keys() -> None:
    assert select_keys(KEYS, 0.3) == select_keys(list(reversed(KEYS)), 0.3)


def test_the_samples_are_nested() -> None:
    """Ce qui est retenu à 10 % l'est à 20 %."""
    assert select_keys(KEYS, 0.1) < select_keys(KEYS, 0.2)


def test_the_sample_spreads_over_the_keys() -> None:
    """Le hash, pas l'ordre : pas un coin de l'arborescence."""
    sample = sorted(select_keys(KEYS, 0.1))

    assert sample != KEYS[:100]


def test_an_empty_source_gives_an_empty_sample() -> None:
    assert select_keys([], 0.5) == set()
