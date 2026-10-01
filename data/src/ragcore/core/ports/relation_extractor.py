from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.relation import Relation
from ..models.unformatted_relation import UnformattedRelation


@dataclass(frozen=True)
class ExtractionResult:
    """Ce que l'extraction a produit, et ce qu'elle n'a pas su nommer.

    Pas de télémétrie injectée dans l'extracteur : ce serait celle du hook, jamais
    réduite dans ``RunStats``. L'appelant tient sa ``WorkerTelemetry`` et déclare les
    inconnus remontés ici.
    """

    relations: list[Relation] = field(default_factory=list)

    unformatted_relations: list[UnformattedRelation] = field(default_factory=list)
    """Les cibles décrites (``@id`` vide), écrites par la saga du document plutôt que
    remontées en phase 2."""

    unknowns: dict[str, list[str]] = field(default_factory=dict)
    """Catégorie -> vocabulaire non traduit (les ``typelien`` inconnus, sous ``links``).
    Un ensemble, pas un compteur."""

    lost_links: int = 0
    """Liens de la source qu'on ne sait pas écrire, comptés en ``relation.unknown`` ; un
    lien retiré par le curseur n'en fait pas partie."""


@runtime_checkable
class BaseRelationExtractor(Protocol):
    """Extraction des liens qu'un document déclare vers d'autres documents."""

    def extract(self, document: ParsedDocument) -> ExtractionResult: ...
