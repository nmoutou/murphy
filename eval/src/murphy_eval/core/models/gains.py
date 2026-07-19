"""La fonction de gain — ce qu'un grade de pertinence *vaut* dans le nDCG.

Deux conventions coexistent dans la littérature IR pour transformer un grade
`0–3` (ADR-005) en gain numérique :

- **exponentielle** `2^rel - 1` (convention par défaut de `trec_eval`) : un
  grade 3 (« support principal ») vaut 7 fois un grade 1, jamais compensé par
  plusieurs documents périphériques bien classés.
- **linéaire** `rel` : un grade 3 vaut 3 fois un grade 1, compensable.

Le choix n'est pas cosmétique : il déplace ce que la métrique récompense. La
métrique de décision (nDCG@R) fige l'**exponentielle** par défaut — alignée
sur l'invariant « le bon document en tête » (`VISION.md`) et sur `trec_eval`,
qui sert d'oracle secondaire. Le **linéaire** reste disponible comme mode
diagnostic : un écart entre les deux est lui-même un signal (« ratisse large
sans remonter le document décisif »), jamais du bruit à ignorer.

La fonction de gain est **injectable** — jamais câblée en dur dans le calcul
du DCG — précisément pour que ce choix reste visible et testable plutôt que
silencieux.
"""

from __future__ import annotations

from collections.abc import Callable

GainFn = Callable[[int], float]
"""Grade de pertinence (0–3, ADR-005) → gain numérique utilisé par le DCG."""


def exponential_gain(rel: int) -> float:
    """Convention par défaut de la métrique de décision (nDCG@R). Alignée
    `trec_eval`. Grades 0/1/2/3 → gains 0/1/3/7.
    """
    return float(2**rel - 1)


def linear_gain(rel: int) -> float:
    """Mode diagnostic optionnel. Grades 0/1/2/3 → gains 0/1/2/3."""
    return float(rel)
