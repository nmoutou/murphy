"""L'échantillon d'un run partiel (ADR-034 §9) : par source, les ⌈ratio × n⌉ clés de
plus petit hash.

Exact (10 % de n, c'est ⌈0,1 × n⌉ clés ; une source d'un fichier garde le sien),
reproductible d'un run à l'autre, et emboîté : ce qui est retenu à 10 % l'est à 20 %.
"""

import heapq
import math
from collections.abc import Collection
from fractions import Fraction
from hashlib import blake2b

from ragcore.core.models.inventory import FULL_RATIO

__all__ = ["select_keys"]

_DIGEST_SIZE = 8


def select_keys(keys: Collection[str], ratio: float) -> set[str]:
    """``ratio`` dans ]0, 1], déjà validé par le plan du run."""
    if ratio >= FULL_RATIO:
        return set(keys)
    # Le ratio décimal du YAML, pas son approximation binaire : 0,7 × 10 vaut 7, pas
    # 7,000000000000001, dont le plafond serait 8
    retained = math.ceil(Fraction(str(ratio)) * len(keys))
    return set(heapq.nsmallest(retained, keys, key=_rank))


def _rank(key: str) -> tuple[bytes, str]:
    """La clé départage deux hashs égaux."""
    return blake2b(key.encode("utf-8"), digest_size=_DIGEST_SIZE).digest(), key
