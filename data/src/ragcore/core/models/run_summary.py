"""Le bilan d'un run : un ``RunStats`` réduit, auquel s'attache l'identité du run.

``RunStats`` n'a pas d'identité et fusionne ; ``RunSummary`` en a une et ne fusionne
pas, faute de réponse commutative à « quel ``run_id`` gagne ? ». L'identité s'attache
donc après la réduction, une seule fois, par ``RunSummary.of()``.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ragcore.core.telemetry_events import (
    DOCUMENT_FAILED,
    DOCUMENT_FETCHED,
    DOCUMENT_INVALIDATED,
    DOCUMENT_PERSISTED,
)

from .collision_tally import CollisionTally
from .enums import SourceName
from .identifiers import RunId
from .run_stats import RunStats
from .unknown_tally import UnknownTally

__all__ = ["RunStatus", "RunSummary"]


class RunStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    """Le run est allé au bout sans tout ingérer. La complétude se lit dans les
    compteurs, elle ne se déduit pas de l'absence d'exception."""
    FAILED = "failed"


class RunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: RunId
    sources: tuple[SourceName, ...]
    """Toujours une liste, même pour une seule source."""

    status: RunStatus
    started_at: datetime
    ended_at: datetime

    counts: dict[str, int]
    """event_type -> nombre de choses comptées ; le statut s'en dérive."""

    unknowns: dict[str, dict[str, UnknownTally]]
    """Ce que le run n'a pas su nommer, par catégorie : pour chaque mot, le nombre de
    documents qui le portent et l'un d'eux. Vide = le vocabulaire a tout couvert."""

    collisions: dict[str, CollisionTally]
    """Les clés de métadonnée qui ont reçu plusieurs valeurs distinctes (ADR-049)."""

    error_message: str | None = None
    """Seulement sur un run ``failed`` : un ``degraded`` n'a pas d'exception, il se lit
    dans les compteurs."""

    @classmethod
    def of(  # noqa: PLR0913 — ce sont les champs d'identité ; les grouper les cacherait
        cls,
        stats: RunStats,
        *,
        context_run_id: RunId,
        sources: tuple[SourceName, ...],
        started_at: datetime,
        status: RunStatus,
        error_message: str | None = None,
        ended_at: datetime | None = None,
    ) -> "RunSummary":
        """Un statut « ok » est vérifié contre les compteurs : l'appelant sait seulement
        si Kedro a levé, pas si des documents ont été perdus en route.
        """
        if status is RunStatus.OK:
            status = _status_from(stats)
        return cls(
            run_id=context_run_id,
            sources=sources,
            status=status,
            started_at=started_at,
            ended_at=ended_at or datetime.now(UTC),
            counts=stats.counts,
            unknowns=stats.unknowns,
            collisions=stats.collisions,
            error_message=error_message,
        )


def _status_from(stats: RunStats) -> RunStatus:
    """``OK`` seulement si tout ce qui a été vu a été ingéré, ou écarté sciemment.

    ``DEGRADED`` sinon, dans deux cas :

    1. ``échoués > 0`` : un document échoué est perdu, même déclaré.
    2. ``vus != ingérés + exclus + échoués`` : des documents ont disparu sans être
       comptés. L'équation ne nomme aucune cause, donc les attrape toutes.

    Le dénominateur est ``document.fetched``, jamais ``document.parsed`` : un document
    invalidé émet ``INVALIDATED`` à la place de ``PARSED``.
    """
    seen = stats.counts.get(DOCUMENT_FETCHED, 0)
    if not seen:
        return RunStatus.OK

    failed = stats.counts.get(DOCUMENT_FAILED, 0)
    accounted = (
        stats.counts.get(DOCUMENT_PERSISTED, 0)
        + stats.counts.get(DOCUMENT_INVALIDATED, 0)
        + failed
    )

    # `!=` et non `<` : un excédent (double comptage) est une anomalie aussi
    if failed or accounted != seen:
        return RunStatus.DEGRADED
    return RunStatus.OK
