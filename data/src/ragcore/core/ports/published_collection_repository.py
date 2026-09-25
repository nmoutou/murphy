from typing import Protocol, runtime_checkable

from ..models.published_collection import PublishedCollection


@runtime_checkable
class PublishedCollectionRepository(Protocol):
    """Le pointeur « quelle collection fait foi » — un singleton, pas un journal.

    ``publish`` écrase : il n'y a qu'une réponse à la question, et c'est la dernière
    publiée par un run ``ok``. L'historique des runs vit dans les ``RunSummary`` ; le
    pointeur, lui, n'a pas de passé — le confondre avec un journal ferait resurgir la
    question « laquelle fait foi ? » à l'intérieur du mécanisme censé y répondre.
    """

    async def publish(self, published: PublishedCollection) -> None: ...

    async def get(self) -> PublishedCollection | None:
        """``None`` = aucun run ``ok`` n'a encore publié. Ce n'est pas une erreur."""
        ...
