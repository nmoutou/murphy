import re
from typing import TYPE_CHECKING, Annotated, Literal, NewType, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from .document import RawDocument

DocumentId = NewType("DocumentId", str)
RunId = NewType("RunId", str)
OwnerId = NewType("OwnerId", str)

_ELI_PATTERN = r"^[A-Z]{8}[0-9]{12}$"

_DOCUMENT_TYPES = {
    "ARTI": "article",
    "TEXT": "texte",
    "SCTA": "section",
}


class ELI(BaseModel):
    """European Legislation Identifier — identifiant métier LEGI.
    
    Responsibilités :
    - Validation de format (N1)
    - Extraction depuis RawDocument (N2)
    - Calcul du type de document
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["eli"] = "eli"
    raw: str

    @field_validator("raw")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if not re.match(_ELI_PATTERN, v):
            raise ValueError(f"Format ELI invalide : {v!r} (attendu : 8 majuscules + 12 chiffres)")
        return v

    @classmethod
    def from_raw_document(cls, raw: "RawDocument") -> "ELI":
        """Extrait et valide l'ELI depuis un RawDocument LEGI.
        
        Lève ValidationError (via le field_validator) si l'ELI est absent ou mal formé.
        """
        from ragcore.core.exceptions import ValidationError

        content = raw.payload.get("content", {})
        eli_str = content.get("eli") or content.get("id", "")
        if not eli_str:
            raise ValidationError("ELI absent du document LEGI")
        return cls(raw=eli_str)

    def serialize(self) -> str:
        """Représentation sérialisée : 'eli:LEGIARTI000006419264'."""
        return f"{self.kind}:{self.raw}"

    @property
    def as_document_id(self) -> DocumentId:
        """Rétrocompatibilité temporaire : convertion vers DocumentId."""
        return DocumentId(self.raw)

    @property
    def document_type(self) -> str:
        """Déduit le type (article, texte, ...) depuis le préfixe ELI."""
        prefix = self.raw[4:8]
        return _DOCUMENT_TYPES.get(prefix, "inconnu")


class JorfId(BaseModel):
    """Identifiant JORF — squelette pour usage futur."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["jorf"] = "jorf"
    raw: str

    def serialize(self) -> str:
        return f"{self.kind}:{self.raw}"


class UploadId(BaseModel):
    """Identifiant pour documents uploadés — SHA-256 de contenu."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["upload"] = "upload"
    raw: str

    def serialize(self) -> str:
        return f"{self.kind}:{self.raw}"


# Union discriminée — Pydantic route automatiquement via le champ 'kind'
SourceIdentifier = Annotated[
    Union[ELI, JorfId, UploadId],
    Field(discriminator="kind"),
]
