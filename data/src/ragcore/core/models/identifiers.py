import re
from typing import NewType

from pydantic import BaseModel, ConfigDict, field_validator

DocumentId = NewType("DocumentId", str)
RunId = NewType("RunId", str)

IDENTIFIER_PATTERN = r"^[A-Z]{8}[0-9]{12}$"

IDENTIFIER_PREFIX_LENGTH = 8


class Identifier(BaseModel):
    """L'identifiant métier d'un document DILA — ``LEGIARTI000006419264``.

    Valide son propre format à la construction (8 majuscules + 12 chiffres) : un
    identifiant mal formé n'existe pas, il lève. Les 8 lettres (``prefix``) disent le
    fonds et la nature du document : ``LEGIARTI``, ``LEGITEXT``, ``JURITEXT``,
    ``JORFTEXT``… Elles suffisent à distinguer un article d'une décision, sans qu'aucun
    type ni aucun marqueur n'ait à le répéter.
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
        """L'identifiant CANONIQUE d'un document : la valeur brute, sans préfixe ajouté.

        C'est la clé Mongo, la clé du payload Qdrant, celle du nœud Neo4j et le
        ``document_id`` des événements d'audit. On la type ``DocumentId`` pour que le
        contrat remonte jusqu'aux sites d'émission.
        """
        return DocumentId(self.raw)

    @property
    def prefix(self) -> str:
        """Les 8 lettres de tête : le fonds et la nature du document."""
        return self.raw[:IDENTIFIER_PREFIX_LENGTH]
