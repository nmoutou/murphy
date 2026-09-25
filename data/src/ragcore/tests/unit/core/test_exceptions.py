import pytest

from ragcore.core.exceptions import ParseError, RagCoreError, ValidationError


def test_parse_error_is_not_caught_as_a_validation_error() -> None:
    """compute_idempotence discrimine les deux par un `except ValidationError`
    placé avant le `except Exception`. Si l'une héritait de l'autre, une des
    deux branches serait inatteignable et le motif de rejet serait faux.
    """
    with pytest.raises(ParseError):
        try:
            raise ParseError("XML illisible")
        except ValidationError:  # ne doit PAS attraper
            pytest.fail("ParseError capturée comme ValidationError")


def test_both_are_domain_errors() -> None:
    assert issubclass(ValidationError, RagCoreError)
    assert issubclass(ParseError, RagCoreError)


def test_message_survives_str() -> None:
    """Les sites d'émission écrivent str(exc) dans le manifest et l'audit."""
    assert str(ValidationError("ELI absent du document LEGI")) == (
        "ELI absent du document LEGI"
    )
