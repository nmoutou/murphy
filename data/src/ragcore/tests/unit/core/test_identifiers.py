from datetime import UTC, datetime

import pytest

from ragcore.core.exceptions import ValidationError
from ragcore.core.models.document import RawDocument
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import ELI, OwnerId
from ragcore.core.services.validation import validate_eli_format

VALID = "LEGIARTI000006419264"


def _raw(content: dict) -> RawDocument:
    return RawDocument(
        source_document_id="whatever.xml",
        owner_id=OwnerId("owner-1"),
        source=SourceName.LEGI,
        payload={"content": content},
        fetched_at=datetime.now(UTC),
    )


def test_serialize_is_prefixed() -> None:
    assert ELI(raw=VALID).serialize() == f"eli:{VALID}"


def test_document_type_reads_the_prefix() -> None:
    assert ELI(raw=VALID).document_type == "article"
    assert ELI(raw="LEGITEXT000006419264").document_type == "texte"
    assert ELI(raw="LEGIXXXX000006419264").document_type == "inconnu"


def test_missing_eli_is_a_validation_error() -> None:
    with pytest.raises(ValidationError, match="absent"):
        ELI.from_raw_document(_raw({}))


def test_malformed_eli_is_a_validation_error_too() -> None:
    """Sans relais explicite, pydantic.ValidationError remonterait et le
    document serait compté comme une erreur de parsing — pas comme un rejet.
    """
    with pytest.raises(ValidationError, match="invalide"):
        ELI.from_raw_document(_raw({"eli": "pas-un-eli"}))


def test_validate_eli_format_shares_the_model_pattern() -> None:
    assert validate_eli_format(VALID)
    assert not validate_eli_format("pas-un-eli")
    assert not validate_eli_format(VALID.lower())
