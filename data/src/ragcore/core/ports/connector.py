from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ..models.document import RawDocument


@runtime_checkable
class BaseConnector(Protocol):
    """Découverte et lecture des documents d'une source.

    Le connector ne comprend rien au contenu qu'il transporte : il localise,
    lit, et emballe. C'est le parser qui interprète — y compris l'identifiant.
    """

    skipped: dict[str, int]
    """Ce que le connecteur a ÉCARTÉ, par raison (artefact d'export, illisible…).

    Fait partie du contrat, pas un détail d'implémentation : écarter un fichier sans
    l'émettre le ferait disparaître AVANT `document.fetched`, donc hors de l'équation
    de complétude. Le node `connect` lit cette table et émet un `document.skipped` par
    écart — c'est la seule façon dont un fichier non-document apparaît au bilan.
    Rempli au fil de `fetch_all`, lisible une fois le générateur épuisé."""

    def fetch_all(self) -> AsyncIterator[RawDocument]:
        """Itère les documents de la source. Générateur : le corpus n'est
        jamais entièrement chargé en mémoire."""
        ...
