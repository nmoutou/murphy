"""La version du contrat de serving, et quand un run a le droit de la publier (ADR-039).

Le backend refuse de démarrer sur une version qu'il ne connaît pas. Le pointeur ne doit
donc JAMAIS annoncer une version que la collection ne respecte pas en entier : un run
restreint n'a réécrit que ses sources, il ne peut pas être celui qui l'introduit.
"""

from ragcore.core.models.identifiers import RunId
from ragcore.core.models.published_collection import (
    SERVING_CONTRACT_VERSION,
    PublishedCollection,
    may_publish,
)


def _pointer(version: int | None) -> PublishedCollection:
    return PublishedCollection(
        collection_name="9424808d",
        fingerprint="9424808d",
        run_id=RunId("r-0"),
        document_count=769,
        serving_contract_version=version,
    )


def test_a_published_pointer_carries_the_contract_version() -> None:
    published = PublishedCollection.of(
        "9424808d", run_id=RunId("r-1"), document_count=1
    )

    assert published.serving_contract_version == SERVING_CONTRACT_VERSION


def test_a_pointer_written_before_the_contract_reads_back_WITHOUT_version() -> None:
    """Un vieux pointeur ne doit pas se faire passer pour la version courante."""
    legacy = PublishedCollection.model_validate(
        {
            "collection_name": "9424808d",
            "fingerprint": "9424808d",
            "run_id": "r-0",
            "document_count": 769,
        }
    )

    assert legacy.serving_contract_version is None


def test_a_full_run_may_always_publish() -> None:
    assert may_publish(None, is_full_run=True)
    assert may_publish(_pointer(None), is_full_run=True)


def test_a_restricted_run_publishes_over_the_SAME_version() -> None:
    assert may_publish(_pointer(SERVING_CONTRACT_VERSION), is_full_run=False)


def test_a_restricted_run_never_INTRODUCES_a_version() -> None:
    assert not may_publish(None, is_full_run=False)
    assert not may_publish(_pointer(None), is_full_run=False)
    assert not may_publish(_pointer(SERVING_CONTRACT_VERSION - 1), is_full_run=False)
