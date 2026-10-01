"""Vocabulaire des catégories d'inconnus.

Même principe que ``exclusion_reasons`` : les sites d'émission importent ces
constantes plutôt que d'écrire les chaînes. **Une catégorie qui n'est pas ici
n'existe pas.**

Un « inconnu » n'est pas une erreur. C'est un AVEU : la source a déclaré un mot
que le domaine ne sait pas encore traduire. Le jeter serait perdre le seul indice
qui dit ce qu'il faudrait apprendre. ``RunStats.unknowns`` le porte jusqu'au
``RunSummary``, où il devient lisible — c'est ainsi que le corpus enseigne son
propre vocabulaire, run après run.
"""

CATEGORY_TAG = "tags"
"""Une métadonnée NON-CONFIGURÉE, sous sa clé chemin-complet (ADR-047, ADR-048) : la
valeur d'une feuille connue sans renommage dans ``meta_renames``, ou celle d'une balise
absente de la table qui a passé la porte metadata.

C'est la vigie de dérive DILA. Émise au site de parse, TOUJOURS — que le curseur
``dev.skip_unconfigured`` retire ou non la métadonnée. On compte d'abord, on filtre
ensuite.
"""

CATEGORY_ROOT = "roots"
"""Une racine XML d'une famille de documents que la source ne connaît pas."""

CATEGORY_LINK = "links"
"""Un type de lien NON-CONFIGURÉ (ADR-048) : un ``typelien`` que la table de la source ne
traduit pas, ou la clé chemin-complet d'une balise absente de la table dont la valeur a
la forme d'un identifiant DILA (lien heuristique).

L'arête est écrite, sauf si le curseur ``dev.skip_unconfigured`` la retire. Un lien qui
ne PEUT PAS être écrit (``sens`` inconnu, ``@id`` illisible) n'est pas un type de lien :
il est compté par ``relation.unknown``, pas ici.
"""

CATEGORY_COLLISION = "collisions"
"""Une clé de métadonnée qui a reçu plusieurs valeurs distinctes dans un document
(ADR-049) : résolue en liste, ou document refusé. Ce n'est pas un mot inconnu, c'est un
choix que la table ne sait pas encore faire."""

UNKNOWN_CATEGORIES = (CATEGORY_TAG, CATEGORY_ROOT, CATEGORY_LINK, CATEGORY_COLLISION)
"""Les catégories du bilan, dans l'ordre où il les présente. Toutes y figurent, même
vides : le schéma de ``run_summaries.unknowns`` ne varie pas d'un run à l'autre."""


def declare_unknown(unknowns: dict[str, list[str]], category: str, value: str) -> None:
    """Consigne un inconnu — **un ENSEMBLE, pas un compteur**.

    « Ce typelien est inconnu », « cette balise est inconnue » : le fait est vrai UNE
    fois, peu importe combien de documents le rencontrent. On dédoublonne donc par
    catégorie. Le parser et l'extracteur de liens le faisaient chacun de leur côté, avec
    la même fonction copiée à l'identique ; elle vit ici, à côté du vocabulaire qu'elle
    remplit.
    """
    known = unknowns.setdefault(category, [])
    if value not in known:
        known.append(value)


__all__ = [
    "CATEGORY_COLLISION",
    "CATEGORY_LINK",
    "CATEGORY_ROOT",
    "CATEGORY_TAG",
    "UNKNOWN_CATEGORIES",
    "declare_unknown",
]
