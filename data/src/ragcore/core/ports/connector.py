from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from ..models.document import RawDocument
from ..models.enums import SourceName
from ..models.inventory import SourceInventory


@runtime_checkable
class BaseConnector(Protocol):
    """Découverte et lecture des documents d'une source, sans les interpréter : c'est le
    rôle du parser, identifiant compris.
    """

    @property
    def skipped(self) -> dict[str, int]:
        """Ce que le connecteur a écarté, par raison (artefact d'export, illisible…).

        La lecture en émet un compteur par raison : sans lui, un fichier écarté
        disparaîtrait avant `document.fetched`, sans trace au bilan. Lisible une fois
        `fetch_all` épuisé."""
        ...

    def discover(self) -> dict[SourceName, SourceInventory]:
        """La passe 1 : l'inventaire de chaque source, sans ouvrir un fichier. Précède
        ``fetch_all``."""
        ...

    def fetch_all(self) -> Iterator[RawDocument]:
        """La passe 2. Synchrone, et générateur : le corpus n'est jamais entièrement
        chargé en mémoire."""
        ...
