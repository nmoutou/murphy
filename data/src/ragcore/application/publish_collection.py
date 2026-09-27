"""CollectionPublisher — publie l'empreinte d'un run, **si et seulement si** il est `ok`.

C'est ici que l'équation de complétude cesse d'être un outil de diagnostic pour devenir
**la condition de publication** (ADR-039). Le pointeur publié est ce que le serving lit :
publier est donc la seule décision de l'ingestion que l'utilisateur voit.
"""

import logging

from ragcore.core.models.published_collection import (
    SERVING_CONTRACT_VERSION,
    PublishedCollection,
    may_publish,
)
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.ports.published_collection_repository import (
    PublishedCollectionRepository,
)
from ragcore.core.telemetry_events import DOCUMENT_PERSISTED

__all__ = ["CollectionPublisher"]

logger = logging.getLogger(__name__)


class CollectionPublisher:
    """La collection d'UN run, et le droit de la publier."""

    def __init__(
        self,
        repo: PublishedCollectionRepository,
        collection_name: str,
        *,
        is_full_run: bool,
    ) -> None:
        self._repo = repo
        self._collection_name = collection_name
        """L'empreinte que ce run écrit, dérivée une fois en tête de run : une seconde
        dérivation serait une seconde occasion de diverger."""
        self._is_full_run = is_full_run
        """Ce run traite-t-il TOUTES les sources ? Seul un run complet peut publier une
        version du contrat que le pointeur en place ne porte pas encore (ADR-039 §3)."""

    async def publish_if_complete(
        self, summary: RunSummary
    ) -> PublishedCollection | None:
        """Publie l'empreinte de ce run — **si et seulement si** le run est `ok`.

        Un run `degraded` a laissé un corpus incomplet : publier son empreinte
        propagerait la fuite jusqu'à l'utilisateur, qui n'aurait aucun moyen de le
        savoir. Le corpus précédent, lui, était complet — le pointeur ne bouge pas, et le
        serving continue de servir le dernier bon.

        Le statut est LU dans le bilan, jamais re-dérivé : deux dérivations sont deux
        occasions de diverger, et celle-ci déciderait de ce que voit l'utilisateur.

        Rend le pointeur publié, ou ``None`` quand il ne bouge pas.
        """
        if summary.status is not RunStatus.OK:
            logger.warning(
                "Run `%s` : le pointeur de collection n'est PAS mis à jour. Le corpus de "
                "ce run est incomplet, le serving continue de servir le précédent.",
                summary.status.value,
            )
            return None

        if not await self._contract_allows_publication():
            return None

        published = PublishedCollection.of(
            self._collection_name,
            run_id=summary.run_id,
            document_count=summary.stats.counts.get(DOCUMENT_PERSISTED, 0),
        )
        await self._repo.publish(published)
        logger.info(
            "Collection publiée : `%s` (%d documents) — c'est elle que le serving lira.",
            published.collection_name,
            published.document_count,
        )
        return published

    async def _contract_allows_publication(self) -> bool:
        """Vérifie que publier ne mêle pas deux versions du contrat (``may_publish``).

        Le pointeur en place est relu ICI, pas en tête de run : c'est la version publiée
        au moment de remplacer le pointeur qui compte.
        """
        current = await self._repo.get()
        if may_publish(current, is_full_run=self._is_full_run):
            return True
        logger.warning(
            "Run restreint : le pointeur de collection n'est PAS mis à jour. Le pointeur "
            "en place ne porte pas la version %d du contrat de serving, et ce run n'a "
            "réécrit que ses sources. Lancer un run complet : "
            "`kedro run --params source=all`.",
            SERVING_CONTRACT_VERSION,
        )
        return False
