import re
from typing import TYPE_CHECKING, Annotated, Literal, NewType

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

from ..exceptions import ValidationError

if TYPE_CHECKING:
    from .document import RawDocument

DocumentId = NewType("DocumentId", str)
RunId = NewType("RunId", str)
OwnerId = NewType("OwnerId", str)

# Public : core/services/validation.py en fait sa source de vérité.
ELI_PATTERN = r"^[A-Z]{8}[0-9]{12}$"

_DOCUMENT_TYPES = {
    "ARTI": "article",
    "TEXT": "texte",
    "SCTA": "section",
}

_JURISDICTIONS = {
    # Mesuré sur les 352 fichiers du corpus juri : trois préfixes, et pas un de plus.
    "JURITEXT": "judiciaire",  # 94 — CAPP, CASS, INCA
    "CETATEXT": "administratif",  # 256 — JADE (Conseil d'État & juridictions admin.)
    "CONSTEXT": "constitutionnel",  # 2 — CONSTIT
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
        if not re.match(ELI_PATTERN, v):
            raise ValueError(
                f"Format ELI invalide : {v!r} (attendu : 8 majuscules + 12 chiffres)"
            )
        return v

    @classmethod
    def from_raw_document(cls, raw: "RawDocument") -> "ELI":
        """Extrait et valide l'ELI depuis un RawDocument LEGI.

        Lève ValidationError si l'ELI est absent (REASON_NO_ELI) ou mal formé
        (REASON_INVALID_ELI) : les deux cas sont des rejets métier, pas des
        erreurs de lecture.
        """
        content = raw.payload.get("content", {})
        eli_str = content.get("eli") or content.get("id", "")
        if not eli_str:
            raise ValidationError("ELI absent du document LEGI")
        try:
            return cls(raw=eli_str)
        except PydanticValidationError as exc:
            # Sans ce relais, le format invalide remonte en pydantic.ValidationError,
            # échappe au `except ValidationError` des appelants, et se fait compter
            # comme une erreur de parsing.
            raise ValidationError(f"Format ELI invalide : {eli_str!r}") from exc

    def serialize(self) -> DocumentId:
        """Représentation sérialisée : 'eli:LEGIARTI000006419264'.

        C'est l'identifiant CANONIQUE d'un document (clé Mongo, document_id des
        événements d'audit) : on le typé `DocumentId` pour que le contrat remonte
        jusqu'aux sites d'émission, sans changer la valeur produite.
        """
        return DocumentId(f"{self.kind}:{self.raw}")

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

    def serialize(self) -> DocumentId:
        return DocumentId(f"{self.kind}:{self.raw}")


class DecisionId(BaseModel):
    """L'identifiant d'une décision de justice — ``JURITEXT…``, ``CETATEXT…``, ``CONSTEXT…``.

    **Pourquoi un type à part, alors que le motif est le même que l'ELI.** Justement :
    ``JURITEXT000019333891`` **satisfait** ``^[A-Z]{8}[0-9]{12}$``. Un ``ELI(raw=…)``
    l'accepterait sans broncher, et la décision serait sérialisée ``eli:JURITEXT…`` — un
    identifiant qui prétend désigner un texte de loi.

    C'est exactement le piège que le routage JORF documente déjà : **le motif ne regarde
    pas le préfixe**. Une jurisprudence rangée sous ``eli:`` ne lèverait aucune exception,
    ne casserait aucun test de format, et polluerait durablement le graphe — jusqu'au jour
    où quelqu'un chercherait pourquoi un « article de loi » a une formation de jugement.

    Un arrêt n'est pas un texte de loi. Le type le dit ; le préfixe seul ne suffisait pas.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["decision"] = "decision"
    raw: str

    @field_validator("raw")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if not re.match(ELI_PATTERN, v):
            raise ValueError(
                f"Format d'identifiant de décision invalide : {v!r} "
                "(attendu : 8 majuscules + 12 chiffres)"
            )
        return v

    def serialize(self) -> DocumentId:
        return DocumentId(f"{self.kind}:{self.raw}")

    @property
    def jurisdiction(self) -> str:
        """L'ordre de juridiction, déduit du préfixe — mesuré sur les 352 fichiers."""
        return _JURISDICTIONS.get(self.raw[:8], "inconnu")


class UploadId(BaseModel):
    """Identifiant pour documents uploadés — SHA-256 de contenu."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["upload"] = "upload"
    raw: str

    def serialize(self) -> DocumentId:
        return DocumentId(f"{self.kind}:{self.raw}")


class UnknownRef(BaseModel):
    """Une cible **décrite** mais pas identifiée. Le « node unknown » du cadrage.

    **Ce qui l'a rendu nécessaire — une mesure, pas une prévision.** Les 68 ``<LIEN>`` du
    corpus de jurisprudence ont **tous leurs attributs vides** : ni ``id``, ni ``cidtexte``,
    ni ``nortexte``. Ce qu'ils portent, c'est du texte : « Articles 1103 et 1229 du code
    civil ». La cour ne pointe pas vers un identifiant — elle *décrit* un article, en
    français, comme le ferait un juriste.

    Sans ce type, ``core/links`` traitait ces liens comme une **donnée absente** et n'en
    faisait aucune arête : le graphe de jurisprudence aurait été vide, en silence. C'était
    vrai pour LEGI (89 attributs vides sur 16 227 : des scories) et radicalement faux
    pour la juri, où c'est le cas normal.

    **Ce n'est pas un état spécial**, et c'est tout l'intérêt. Le principe directeur du
    cadrage : *« Ce qui n'est pas encore résolu n'est pas un état spécial — c'est un node
    unknown qui attend sa passe de résolution. »* La citation existe, elle est dans le
    graphe, elle est visible, elle est interrogeable. Ce qui manque, c'est son *identité*
    — et une passe de résolution ultérieure (extracteur de références + registre d'alias,
    §1/§7) la lui donnera **sans re-ingérer quoi que ce soit** : le texte est déjà là.

    ``raw`` est le libellé brut, littéral. On ne le parse pas ici — le parser d'une source
    ne sait pas ce qu'est un code juridique, et prétendre le contraire remettrait de la
    sémantique dans le connecteur.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["unknown"] = "unknown"
    raw: str

    def serialize(self) -> DocumentId:
        return DocumentId(f"{self.kind}:{self.raw}")


# Union discriminée — Pydantic route automatiquement via le champ 'kind'
SourceIdentifier = Annotated[
    ELI | JorfId | DecisionId | UploadId | UnknownRef,
    Field(discriminator="kind"),
]

_IDENTIFIER_KINDS: dict[
    str,
    type[ELI] | type[JorfId] | type[DecisionId] | type[UploadId] | type[UnknownRef],
] = {
    "eli": ELI,
    "jorf": JorfId,
    "decision": DecisionId,
    "upload": UploadId,
    "unknown": UnknownRef,
}


def deserialize_identifier(value: str) -> "SourceIdentifier":
    """Inverse de ``serialize()`` : ``'eli:LEGIARTI…'`` → ``ELI(raw='LEGIARTI…')``.

    Le cache des relations pendantes (§13) stocke des identifiants sérialisés.
    Sans ce retour, il serait une voie sans issue : on saurait écrire une clé,
    pas la relire pour rejouer la relation.
    """
    kind, separator, raw = value.partition(":")
    if not separator or kind not in _IDENTIFIER_KINDS:
        raise ValidationError(f"Identifiant sérialisé inconnu : {value!r}")
    try:
        return _IDENTIFIER_KINDS[kind](raw=raw)
    except PydanticValidationError as exc:
        raise ValidationError(f"Identifiant sérialisé invalide : {value!r}") from exc
