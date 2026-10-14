import pytest

from ragcore.core.exceptions import (
    CollisionError,
    ParseError,
    RagCoreError,
    ValidationError,
)
from ragcore.core.services.exclusion_reasons import (
    REASON_COLLISION,
    REASON_IDENTIFIER_MISSING,
)


def test_parse_error_is_not_caught_as_a_validation_error() -> None:
    """parse_documents les distingue par un `except ValidationError` placé avant
    `except ParseError` : un héritage rendrait une branche inatteignable."""
    with pytest.raises(ParseError):
        try:
            raise ParseError("XML illisible")
        except ValidationError:  # ne doit pas attraper
            pytest.fail("ParseError capturée comme ValidationError")


def test_both_are_domain_errors() -> None:
    assert issubclass(ValidationError, RagCoreError)
    assert issubclass(ParseError, RagCoreError)


def test_message_survives_str() -> None:
    """Les sites d'émission écrivent str(exc) dans l'audit."""
    error = ValidationError(REASON_IDENTIFIER_MISSING, "ELI absent du document LEGI")

    assert str(error) == "ELI absent du document LEGI"
    assert error.reason == REASON_IDENTIFIER_MISSING


def test_une_collision_porte_sa_raison() -> None:
    assert CollisionError("num en collision", ()).reason == REASON_COLLISION
