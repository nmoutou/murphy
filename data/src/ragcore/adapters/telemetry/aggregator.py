"""Agrégateur in-memory des AuditEvent — l'agrégat local d'UN worker.

Le ``threading.Lock`` d'avant a disparu, et pas par négligence : il protégeait un
``defaultdict`` mutable partagé. L'agrégat est désormais un ``RunStats`` immuable
que chaque ``emit`` remplace — il n'y a plus d'état à corrompre, donc plus rien à
verrouiller. C'est l'invariant 1 du pool (§11) appliqué ici : le verrou disparaît
par construction, pas par discipline.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.telemetry_events import (
    DOCUMENT_FAILED,
    DOCUMENT_INVALIDATED,
    DOCUMENT_PERSISTED,
)

# Events dont on veut un breakdown par clé de payload.
_BREAKDOWN_KEY: dict[str, str] = {
    DOCUMENT_INVALIDATED: "reason",   # breakdown par raison de rejet
    DOCUMENT_PERSISTED: "operation",  # breakdown par opération (INSERT/UPDATE)
    DOCUMENT_FAILED: "reason",        # breakdown par CAUSE de la fuite
}


def _weight_of(payload: dict[str, Any]) -> int:
    """Le POIDS d'un event : combien de choses il rapporte, pas combien de fois il tinte.

    La plupart des events valent 1 — un document persisté, un document parsé. Mais
    certains sont émis **une fois pour un lot** et portent leur cardinalité en payload :
    ``document.fetched`` avec ``{"count": 1121}``, ``relation.upserted`` avec le nombre
    d'arêtes écrites. Les compter pour 1 (ce qu'on faisait) donnait un RunSummary qui
    annonçait ``document.fetched: 1`` sur un run de 1121 documents — et rendait le critère
    de fin (« ingérés + exclus + échoués = total vu ») **invérifiable depuis le bilan**.

    Émettre 1121 events à la place coûterait 1121 écritures d'audit pour une information
    déjà connue. Le ``count`` du payload est la réponse : les émetteurs le posaient déjà,
    l'agrégateur ne le lisait pas.

    Défensif sur le type : un payload est une donnée de télémétrie, pas un contrat typé.
    Un ``count`` non entier ne doit pas faire tomber le bilan du run.
    """
    count = payload.get("count")
    return count if isinstance(count, int) and count >= 0 else 1


class RunStatsAggregator:
    """Agrège les AuditEvent en un ``RunStats``. Satisfait ``WorkerTelemetry``.

    ``snapshot()`` rend l'agrégat brut — c'est lui qu'on fusionne entre workers.
    ``finalize()`` y attache l'identité du run pour produire le ``RunSummary`` ;
    la persistance (fichier JSON + Mongo) reste à l'orchestrateur.
    """

    def __init__(
        self,
        run_id: RunId,
        owner_id: OwnerId,
        source: SourceName | None,
        started_at: datetime,
    ) -> None:
        self._run_id = run_id
        self._owner_id = owner_id
        self._source = source
        self._started_at = started_at
        self._stats = RunStats.empty()

    @property
    def counts(self) -> dict[str, int]:
        return dict(self._stats.counts)

    def emit(self, event: AuditEvent) -> None:
        payload = event.payload or {}
        weight = _weight_of(payload)
        stats = self._stats.with_count(event.event_type, weight)

        payload_key = _BREAKDOWN_KEY.get(event.event_type)
        if payload_key is not None:
            value = payload.get(payload_key, "unknown")
            stats = stats.with_breakdown(event.event_type, value)

        # ⚠️ DETTE : PAS de ventilation par source. Sur un run multi-source, le bilan dit
        # « 3 compensations » sans dire *chez qui* — donc il faut tout rejouer, faute de
        # savoir quoi rejouer. La matière est pourtant là : `ingest_document` estampille
        # `source=parsed.source` (la source du DOCUMENT, correcte même quand le contexte du
        # run vaut `None`).
        #
        # Ce qui manque n'est pas une ligne ici, c'est un CHAMP : `breakdowns` est
        # `event_type -> {clé -> compte}` et ses deux places sont prises (`reason`,
        # `operation`). Ventiler par source demande un axe de plus — un `by_source` sur
        # `RunStats`, de même forme et de même monoïde. Le bricoler ici (clé composite
        # `"legi:document.persisted"`) donnerait un bilan qu'il faudrait re-parser pour
        # lire. C'est du §12, et ça se fait dans le modèle, pas dans l'adaptateur.

        self._stats = stats

    def log(self, level: str, message: str, **context: Any) -> None:  # noqa: ARG002
        return

    def record_unknown(self, category: str, value: str) -> None:
        """Un vocabulaire non reconnu se DÉCLARE — il ne se jette pas en silence."""
        self._stats = self._stats.with_unknown(category, value)

    def snapshot(self) -> RunStats:
        """L'agrégat local, à fusionner avec celui des autres workers."""
        return self._stats

    def absorb(self, stats: RunStats) -> None:
        """Fusionne un agrégat venu d'AILLEURS — typiquement celui des workers.

        Sans ceci, l'agrégateur du hook ne voit que les events du process principal.
        Or les compensations de saga arrivent **dans les workers** : leur compteur
        restait donc structurellement nul, et ``_status_from`` rendait *toujours*
        ``ok``. Un statut dérivé d'un compteur jamais alimenté n'est pas un statut
        dérivé — c'est un ``ok`` en dur avec plus d'étapes.

        La fusion est sûre par construction : ``RunStats`` est un monoïde commutatif,
        donc absorber dans n'importe quel ordre donne le même bilan (§11).
        """
        self._stats = self._stats.merge(stats)

    def close(self) -> None:
        """Rien à drainer : l'agrégat vit en mémoire."""
        return

    def finalize(
        self, status: RunStatus, error_message: str | None = None
    ) -> RunSummary:
        """Projette l'agrégat en RunSummary — l'identité s'attache ici, une fois."""
        return RunSummary.of(
            self._stats,
            context_run_id=self._run_id,
            owner_id=self._owner_id,
            source=self._source,
            started_at=self._started_at,
            status=RunStatus(status),
            error_message=error_message,
            ended_at=datetime.now(UTC),
        )
