from ragcore.core.models.identifiers import ELI
from ragcore.core.services.validation import validate_eli_format

VALID = "LEGIARTI000006419264"


def test_serialize_is_prefixed() -> None:
    assert ELI(raw=VALID).serialize() == f"eli:{VALID}"


def test_document_type_reads_the_prefix() -> None:
    assert ELI(raw=VALID).document_type == "article"
    assert ELI(raw="LEGITEXT000006419264").document_type == "texte"
    assert ELI(raw="LEGIXXXX000006419264").document_type == "inconnu"


def test_validate_eli_format_shares_the_model_pattern() -> None:
    assert validate_eli_format(VALID)
    assert not validate_eli_format("pas-un-eli")
    assert not validate_eli_format(VALID.lower())
