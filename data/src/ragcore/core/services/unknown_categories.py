"""Les catégories d'inconnus : une catégorie qui n'est pas ici n'existe pas.

Un inconnu n'est pas une erreur : c'est un mot de la source que le domaine ne sait pas
encore traduire, et l'indice de ce qu'il faudrait apprendre.
"""

CATEGORY_TAG = "tags"
"""Une métadonnée non configurée, sous sa clé chemin-complet (ADR-047, ADR-048). La
vigie de dérive DILA : émise même quand ``skip_unconfigured`` retire la métadonnée.
"""

CATEGORY_ROOT = "roots"
"""Une racine XML d'une famille de documents que la source ne connaît pas."""

CATEGORY_LINK = "links"
"""Un type de lien non configuré (ADR-048) : ``typelien`` non traduit, ou lien
heuristique. Un lien qui ne peut pas être écrit est compté par ``relation.unknown``.
"""

UNKNOWN_CATEGORIES = (CATEGORY_TAG, CATEGORY_ROOT, CATEGORY_LINK)
"""Dans l'ordre du bilan. Toutes y figurent, même vides : le schéma de
``run_summaries.unknowns`` ne varie pas d'un run à l'autre."""


def declare_unknown(unknowns: dict[str, list[str]], category: str, value: str) -> None:
    """Un ensemble, pas un compteur : dédoublonné par catégorie."""
    known = unknowns.setdefault(category, [])
    if value not in known:
        known.append(value)


__all__ = [
    "CATEGORY_LINK",
    "CATEGORY_ROOT",
    "CATEGORY_TAG",
    "UNKNOWN_CATEGORIES",
    "declare_unknown",
]
