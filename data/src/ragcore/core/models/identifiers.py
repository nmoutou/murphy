import re
from typing import NewType

from pydantic import BaseModel, ConfigDict, field_validator

DocumentId = NewType("DocumentId", str)
RunId = NewType("RunId", str)

IDENTIFIER_PATTERN = r"^[A-Z]{8}[0-9]{12}$"

IDENTIFIER_PREFIX_LENGTH = 8


class Identifier(BaseModel):
    """L'identifiant d'un document DILA — ``LEGIARTI000006419264``. Mal formé, il lève
    à la construction.
    """

    model_config = ConfigDict(frozen=True)

    raw: str

    @field_validator("raw")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if not re.match(IDENTIFIER_PATTERN, v):
            raise ValueError(
                f"Format d'identifiant invalide : {v!r} "
                "(attendu : 8 majuscules + 12 chiffres)"
            )
        return v

    def serialize(self) -> DocumentId:
        """La valeur brute, sans préfixe : clé Mongo, ``_id`` OpenSearch, clé du nœud
        Neo4j, et ``document_id`` des événements d'audit.
        """
        return DocumentId(self.raw)

    @property
    def prefix(self) -> str:
        """Le fonds et la nature du document : ``LEGIARTI``, ``JURITEXT``…"""
        return self.raw[:IDENTIFIER_PREFIX_LENGTH]
