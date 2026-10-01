from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ..models.document import RawDocument


@runtime_checkable
class BaseConnector(Protocol):
    """Découverte et lecture des documents d'une source, sans les interpréter : c'est le
    rôle du parser, identifiant compris.
    """

    skipped: dict[str, int]
    """Ce que le connecteur a écarté, par raison (artefact d'export, illisible…).

    Le nœud `connect` en émet un compteur par raison : sans lui, un fichier écarté
    disparaîtrait avant `document.fetched`, sans trace au bilan. Lisible une fois
    `fetch_all` épuisé."""

    def fetch_all(self) -> AsyncIterator[RawDocument]:
        """Générateur : le corpus n'est jamais entièrement chargé en mémoire."""
        ...
