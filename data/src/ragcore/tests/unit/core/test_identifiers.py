import pytest
from pydantic import ValidationError

from ragcore.core.models.identifiers import Identifier

VALID = "LEGIARTI000006419264"


def test_serialize_is_the_raw_value() -> None:
    assert Identifier(raw=VALID).serialize() == VALID


def test_prefix_is_the_eight_leading_letters() -> None:
    assert Identifier(raw=VALID).prefix == "LEGIARTI"
    assert Identifier(raw="JURITEXT000019333891").prefix == "JURITEXT"


@pytest.mark.parametrize("malformed", ["pas-un-identifiant", VALID.lower(), ""])
def test_a_malformed_identifier_does_not_exist(malformed: str) -> None:
    with pytest.raises(ValidationError, match="Format d'identifiant invalide"):
        Identifier(raw=malformed)
