from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ..models.document import RawDocument
from ..models.identifiers import OwnerId


@runtime_checkable
class BaseConnector(Protocol):
    """Découverte et lecture des documents d'une source.

    Le connector ne comprend rien au contenu qu'il transporte : il localise,
    lit, et emballe. C'est le parser qui interprète — y compris l'identifiant.
    """

    def fetch_all(self, owner_id: OwnerId) -> AsyncIterator[RawDocument]:
        """Itère les documents de la source. Générateur : le corpus n'est
        jamais entièrement chargé en mémoire."""
        ...
