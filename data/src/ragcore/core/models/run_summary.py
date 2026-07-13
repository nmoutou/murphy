"""RunSummary — la PROJECTION identifiée d'un RunStats.

Deux modèles, deux natures, et la frontière n'est pas cosmétique :

- ``RunStats`` est *calculé*. Il n'a pas d'identité, il fusionne (monoïde), et il
  en existe N par run — un par worker.
- ``RunSummary`` est *déclaré*. Il porte l'identité du run (run_id, owner, dates,
  statut) et il en existe exactement UN. Il ne fusionne pas.

Confondre les deux obligerait à répondre à « quel ``run_id`` gagne quand on fusionne
deux sommaires ? » — question sans réponse commutative, donc source de
non-déterminisme silencieux. On ne la pose jamais : l'identité s'attache APRÈS la
réduction, une seule fois, par ``RunSummary.of()``.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ragcore.core.telemetry_events import SAGA_COMPENSATION_STARTED

from .document import SCHEMA_VERSION
from .enums import SourceName
from .identifiers import OwnerId, RunId
from .run_stats import RunStats

__all__ = ["RunStatus", "RunSummary"]


class RunStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    """Le run est allé au bout, mais il n'a PAS tout ingéré.

    Distinct de FAILED (le pipeline a levé, rien ne garantit l'état des stores) et
    distinct d'OK (tout ce qui a été vu a été ingéré). Sans ce troisième état, un run
    qui compense trois sagas — donc qui perd trois documents — se déclare « ok » au
    seul motif qu'aucune exception n'est remontée à Kedro. C'est le « critère faible »
    que la doctrine rejette : la complétude se LIT dans les compteurs, elle ne se
    déduit pas de l'absence d'exception.
    """
    FAILED = "failed"


class RunSummary(BaseModel):
    """Bilan d'un run : son identité, et l'agrégat qu'il a produit."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = SCHEMA_VERSION

    run_id: RunId
    owner_id: OwnerId
    source: SourceName | None

    status: RunStatus
    started_at: datetime
    ended_at: datetime

    stats: RunStats = Field(default_factory=RunStats.empty)
    """Ce que le run a compté, et ce qu'il n'a pas su nommer (``stats.unknowns``).

    Un run qui ne comprend pas tout reste un run valide, mais il doit le dire :
    rien n'est jeté en silence. ``unknowns`` vide = le vocabulaire a tout couvert.
    """

    error_message: str | None = None

    @classmethod
    def of(  # noqa: PLR0913 — ce SONT les champs d'identité ; les grouper les cacherait
        cls,
        stats: RunStats,
        *,
        context_run_id: RunId,
        owner_id: OwnerId,
        source: SourceName | None,
        started_at: datetime,
        status: RunStatus,
        error_message: str | None = None,
        ended_at: datetime | None = None,
    ) -> "RunSummary":
        """Attache l'identité du run à l'agrégat réduit — la projection, une fois.

        Le statut annoncé « ok » est **vérifié contre les compteurs**, jamais cru sur
        parole : l'appelant ne sait que si Kedro a levé, il ne sait pas si des
        documents ont été perdus en route.
        """
        if status is RunStatus.OK:
            status = _status_from(stats)
        return cls(
            run_id=context_run_id,
            owner_id=owner_id,
            source=source,
            status=status,
            started_at=started_at,
            ended_at=ended_at or datetime.now(UTC),
            stats=stats,
            error_message=error_message,
        )


def _status_from(stats: RunStats) -> RunStatus:
    """OK seulement si aucune saga n'a compensé.

    Une compensation, c'est un document que la saga a défait dans les trois stores :
    il a été vu, il n'est pas ingéré, et le run n'est donc pas complet. Le déclarer
    « ok » ferait mentir le critère de fin (« ingérés + exclus + échoués = total vu »)
    au moment précis où il compte.
    """
    compensated = stats.counts.get(SAGA_COMPENSATION_STARTED, 0)
    return RunStatus.DEGRADED if compensated else RunStatus.OK
