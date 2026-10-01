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

CATEGORY_TYPELIEN = "typelien"
"""Un ``<LIEN typelien="…">`` dont le verbe n'est pas dans la table de la source."""

CATEGORY_SENS = "sens"
"""Un ``<LIEN sens="…">`` qui n'est ni ``source`` ni ``cible`` : l'arête ne peut
pas être orientée, donc pas construite."""

CATEGORY_UNCONFIGURED_TAG = "tag.unconfigured"
"""Une balise XML NON-CONFIGURÉE — la vigie de dérive DILA (ADR-022 §1, ADR-047) :
absente de la table de rôles, ou connue mais sans renommage dans ``meta_renames``.

Ce n'est plus un « unknown » dans la donnée : la balise a été ROUTÉE (porte metadata ou
porte liens, cascade des « trois portes ») et ce compteur est le signal qui survit au
routage. Émis au site de parse, TOUJOURS — que le curseur ``dev.skip_unconfigured``
retire ou non les métadonnées. On compte d'abord, on filtre ensuite.
"""

CATEGORY_ROOT = "racine"
"""Une racine XML d'une famille de documents que la source ne connaît pas."""

CATEGORY_IDENTIFIER = "identifiant"
"""Un ``@id`` PRÉSENT mais que la table de la source ne sait pas transformer en
identifiant (format inattendu). À distinguer d'un ``@id`` VIDE, qui est une absence
de donnée, pas un inconnu. Le taire ferait disparaître l'arête en silence — le lien
existait pourtant, la source l'a écrit."""


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
    "CATEGORY_IDENTIFIER",
    "CATEGORY_ROOT",
    "CATEGORY_SENS",
    "CATEGORY_TYPELIEN",
    "CATEGORY_UNCONFIGURED_TAG",
    "declare_unknown",
]
