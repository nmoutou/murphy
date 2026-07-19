"""``Judgment`` — une ligne du fichier qrels canonique (ADR-008).

Le format canonique est JSONL versionné, un jugement par ligne, portant les
réponses `q1/q2/q3` de la cascade (ADR-005) en plus du `grade` qu'elles
dérivent — redondance assumée : elle permet de localiser un désaccord à la
question près et de re-dériver le grade sans tout ré-annoter.

Pour B-04 (le scorer), seuls `query_id`, `chunk_id`, `doc_id` et `grade` sont
porteurs : le reste du modèle existe pour que ce même type serve tel quel à
l'outil d'annotation (alpha, ADR-010) et aux projections de B-05, sans
duplication de schéma.
"""

from __future__ import annotations

from pydantic import Field

from murphy_eval.core.models._base import Frozen


class Judgment(Frozen):
    """Un jugement de pertinence gradué, au niveau chunk (ADR-005/008)."""

    query_id: str
    doc_id: str
    chunk_id: str
    grade: int = Field(ge=0, le=3)
    q1: bool | None = None
    q2: bool | None = None
    q3: bool | None = None
    origin: str = ""
    annotator: str = ""
    timestamp: str = ""
    guide_version: str = ""


class Qrels(Frozen):
    """L'ensemble des jugements d'une collection de test, niveau chunk."""

    judgments: tuple[Judgment, ...]

    def by_query(self) -> dict[str, list[Judgment]]:
        """Groupe les jugements par requête, dans l'ordre d'apparition."""
        grouped: dict[str, list[Judgment]] = {}
        for judgment in self.judgments:
            grouped.setdefault(judgment.query_id, []).append(judgment)
        return grouped
