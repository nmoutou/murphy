from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.document import ParsedDocument
from ..models.relation import Relation
from ..models.unformatted_relation import UnformattedRelation


@dataclass(frozen=True)
class ExtractionResult:
    """Ce que l'extraction a vraiment produit — et ce qu'elle n'a pas su nommer.

    Même raisonnement que ``RelationWriteResult`` (§12), un cran plus tôt dans la
    chaîne. ``extract() -> list[Relation]`` était *structurellement incapable*
    d'exprimer un rejet : un ``typelien`` hors du vocabulaire tombait dans un
    ``except ValueError: continue``, et l'arête s'évaporait sans laisser de trace.
    Une liste ne peut pas dire « j'ai vu ce mot et je ne l'ai pas compris ».

    Ce type le peut. L'inconnu n'est pas une erreur — c'est une DONNÉE, et il voyage
    donc dans la donnée, exactement comme une arête différée voyage dans ``.pending``.

    Pourquoi pas une télémétrie injectée dans l'extracteur ? Parce qu'il ne tourne pas
    dans le même worker que celui qui écrit le bilan : lui passer une pile de
    télémétrie, ce serait lui passer celle du hook — celle qui n'est jamais réduite
    dans ``RunStats``. Ça marcherait par accident, et casserait dès que le pool
    existe. L'appelant, lui, TIENT sa ``WorkerTelemetry`` : c'est à lui de déclarer
    (``record_unknown``) ce que l'extracteur lui remonte.
    """

    relations: list[Relation] = field(default_factory=list)

    unformatted_relations: list[UnformattedRelation] = field(default_factory=list)
    """Les cibles DÉCRITES (``@id`` vide) — des relations non formatées, jamais une arête.

    Elles ne remontent pas vers la phase 2 comme les relations : elles rejoignent la
    saga du document, qui les écrit dans ``unformatted_relations``. Voir
    ``core.models.unformatted_relation``.
    """

    unknowns: dict[str, list[str]] = field(default_factory=dict)
    """Catégorie (cf. ``core.services.unknown_categories``) -> vocabulaire non traduit :
    les ``typelien`` inconnus, sous ``links``.

    Un ENSEMBLE, pas un compteur : « le typelien ``ZORGLUB`` est inconnu » est vrai
    une fois pour toutes. Vide = le vocabulaire de la source a tout couvert.
    """

    lost_links: int = 0
    """Les liens que la source a écrits mais qu'on ne sait pas écrire (``sens`` inconnu,
    ``@id`` illisible, ``typelien`` qui ne peut pas être un verbe). L'appelant les compte
    en ``relation.unknown`` ; un lien retiré par le curseur n'en fait pas partie."""


@runtime_checkable
class BaseRelationExtractor(Protocol):
    """Extraction des liens qu'un document déclare vers d'autres documents.

    Rend un ``ExtractionResult`` et non une liste : ce que l'extracteur ne sait pas
    traduire doit RESSORTIR, pas disparaître.
    """

    def extract(self, document: ParsedDocument) -> ExtractionResult: ...
