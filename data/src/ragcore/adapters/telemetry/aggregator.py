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
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.telemetry_events import COUNT_CARRYING_EVENTS, PAYLOAD_COUNT_KEY


def _weight_of(event_type: str, payload: dict[str, Any]) -> int:
    """Le POIDS d'un event : combien de choses il rapporte, pas combien de fois il tinte.

    La plupart des events valent 1 — un document persisté, un document parsé. Seuls ceux
    déclarés PORTEURS DE CARDINALITÉ (``COUNT_CARRYING_EVENTS``) sont émis **une fois pour
    un lot** et portent leur compte en payload : ``document.fetched`` avec le nombre de
    documents vus, ``relation.upserted`` avec le nombre d'arêtes écrites. Les compter pour
    1 donnait un RunSummary qui annonçait ``document.fetched: 1`` sur un run de 1121
    documents — et rendait le critère de fin (« ingérés + exclus + échoués = total vu »)
    **invérifiable depuis le bilan**.

    **Le contrat est explicite, pas déduit de la clé.** On ne lit ``payload[count]`` que
    pour un event qui a DÉCLARÉ le porter (cf. ``telemetry_events.py``). Un ``count`` qui
    traînerait dans le payload d'un event unitaire est ignoré ; et renommer la clé d'un
    émetteur porteur casserait le golden du catalogue, pas le bilan en silence.

    Défensif sur le type : un payload est une donnée de télémétrie, pas un contrat typé.
    Un ``count`` non entier ne doit pas faire tomber le bilan du run.
    """
    if event_type not in COUNT_CARRYING_EVENTS:
        return 1
    count = payload.get(PAYLOAD_COUNT_KEY)
    return count if isinstance(count, int) and count >= 0 else 1


class RunStatsAggregator:
    """Agrège les AuditEvent en un ``RunStats``. Satisfait ``WorkerTelemetry``.

    ``snapshot()`` rend l'agrégat brut — c'est lui qu'on fusionne entre workers.
    ``finalize()`` y attache l'identité du run pour produire le ``RunSummary`` ;
    la persistance (Mongo) reste à l'orchestrateur.
    """

    def __init__(
        self,
        run_id: RunId,
        sources: tuple[SourceName, ...],
        started_at: datetime,
    ) -> None:
        self._run_id = run_id
        self._sources = sources
        self._started_at = started_at
        self._stats = RunStats.empty()

    @property
    def counts(self) -> dict[str, int]:
        return dict(self._stats.counts)

    def emit(self, event: AuditEvent) -> None:
        weight = _weight_of(event.event_type, event.payload or {})
        # ⚠️ DETTE : PAS de compteurs par source. Sur un run multi-source, le bilan dit
        # « 3 compensations » sans dire *chez qui*. Compter par source demanderait un
        # axe de plus sur `RunStats`, de même monoïde : ça se fait dans le modèle, pas ici.
        self._stats = self._stats.with_count(event.event_type, weight)

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
        """Rien à fermer : l'agrégat vit en mémoire."""
        return

    def finalize(
        self, status: RunStatus, error_message: str | None = None
    ) -> RunSummary:
        """Projette l'agrégat en RunSummary — l'identité s'attache ici, une fois."""
        return RunSummary.of(
            self._stats,
            context_run_id=self._run_id,
            sources=self._sources,
            started_at=self._started_at,
            status=RunStatus(status),
            error_message=error_message,
            ended_at=datetime.now(UTC),
        )
