"""Ce qu'une source déclare de ses liens : sa ``LinkTable``. Une donnée, jamais du code."""

from __future__ import annotations

from dataclasses import dataclass

from .vocabulary import TranslationTable

__all__ = ["LinkTable"]


@dataclass(frozen=True)
class LinkTable:
    """Ce qu'une SOURCE déclare de ses liens. Une donnée, jamais du code.

    C'est le pendant, pour les arêtes, de la table de rôles pour les balises : la
    saturation d'un corpus la remplit, et un cliquet la fige. Une source nouvelle =
    une table.
    """

    translation: TranslationTable
    """Le vocabulaire de la source vers celui du domaine (``"CITATION" -> cites``).

    Exhaustive AUJOURD'HUI, jamais demain — et c'est prévu : ce qu'elle ne contient pas
    entre sous son nom brut et remonte dans ``unknowns``. Le corpus enseigne son
    vocabulaire ; la table apprend.
    """

    structural_kinds: frozenset[str] = frozenset()
    """Les balises de lien dont l'orientation est connue PAR CONSTRUCTION.

    Une section contient ses articles ; un texte contient ses sections. Ce sens-là ne
    peut pas s'inverser, et ces balises ne portent donc ni ``typelien`` ni ``sens``.
    Elles produisent toutes un ``CONTAINS`` — du document courant VERS le lié.
    """

    ancestor_kinds: frozenset[str] = frozenset()
    """Les balises qui déclarent un ANCÊTRE du document (le ``<CONTEXTE>`` de LEGI).

    L'arête va de l'ancêtre VERS le document courant : orientation fixe, jamais ambiguë.
    C'est la fermeture transitive de la contenance — d'où la réduction, en phase 2.
    """
