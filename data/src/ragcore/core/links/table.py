"""Ce qu'une source déclare de ses liens : sa ``LinkTable``. Une donnée, jamais du code."""

from __future__ import annotations

from dataclasses import dataclass

from .vocabulary import TranslationTable

__all__ = ["LinkTable"]


@dataclass(frozen=True)
class LinkTable:
    """Le pendant, pour les arêtes, de la table de rôles pour les balises."""

    translation: TranslationTable
    """Le vocabulaire de la source vers celui du domaine (``"CITATION" -> cites``). Ce
    qu'elle ne contient pas entre sous son nom brut et remonte dans ``unknowns``.
    """

    structural_kinds: frozenset[str] = frozenset()
    """Balises de contenance, sans ``typelien`` ni ``sens`` : toutes donnent un
    ``CONTAINS`` du document courant vers le lié.
    """

    ancestor_kinds: frozenset[str] = frozenset()
    """Balises qui déclarent un ancêtre du document (le ``<CONTEXTE>`` de LEGI) : l'arête
    va de l'ancêtre vers le document courant. Fermeture transitive de la contenance,
    d'où la réduction en phase 2.
    """
