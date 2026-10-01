"""RunSummary — la PROJECTION identifiée d'un RunStats.

Deux modèles, deux natures, et la frontière n'est pas cosmétique :

- ``RunStats`` est *calculé*. Il n'a pas d'identité, il fusionne (monoïde), et il
  en existe N par run — un par worker.
- ``RunSummary`` est *déclaré*. Il porte l'identité du run (run_id, sources, dates,
  statut) et il en existe exactement UN. Il ne fusionne pas. Il recopie à plat les
  compteurs, les inconnus et les collisions de l'agrégat : c'est le document de ``run_summaries``.

Confondre les deux obligerait à répondre à « quel ``run_id`` gagne quand on fusionne
deux sommaires ? » — question sans réponse commutative, donc source de
non-déterminisme silencieux. On ne la pose jamais : l'identité s'attache APRÈS la
réduction, une seule fois, par ``RunSummary.of()``.
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

    run_id: RunId
    sources: tuple[SourceName, ...]
    """Les sources ingérées : toujours une liste, même pour une seule."""

    status: RunStatus
    started_at: datetime
    ended_at: datetime

    counts: dict[str, int]
    """event_type -> nombre de choses comptées. C'est d'eux que le statut se dérive."""

    unknowns: dict[str, dict[str, UnknownTally]]
    """Ce que le run n'a pas su nommer, par catégorie : pour chaque mot, le nombre de
    documents qui le portent et l'un d'eux.

    Un run qui ne comprend pas tout reste un run valide, mais il doit le dire :
    rien n'est jeté en silence. Vide = le vocabulaire a tout couvert.
    """

    collisions: dict[str, CollisionTally]
    """Les clés de métadonnée qui ont reçu plusieurs valeurs distinctes (ADR-049) : pour
    chacune, le nombre de documents et les fichiers de l'un d'eux. Rangées en liste ou
    refusées, elles ne sont pas des inconnus."""

    error_message: str | None = None
    """Seulement sur un run ``failed`` : un ``degraded`` n'a pas d'exception, il se lit
    dans les compteurs."""

    @classmethod
    def of(  # noqa: PLR0913 — ce SONT les champs d'identité ; les grouper les cacherait
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
        """Attache l'identité du run à l'agrégat réduit — la projection, une fois.

        Le statut annoncé « ok » est **vérifié contre les compteurs**, jamais cru sur
        parole : l'appelant ne sait que si Kedro a levé, il ne sait pas si des
        documents ont été perdus en route.
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
    """``OK`` seulement si TOUT ce qui a été vu a été ingéré — ou écarté sciemment.

    Deux propriétés distinctes, qu'il ne faut pas confondre, et qui mènent toutes deux à
    ``DEGRADED`` :

    1. **Le run a-t-il tout ingéré ?**  ``échoués == 0``.
       Un document qui échoue est un document perdu, *même déclaré*. Le déclarer le rend
       rejouable ; ça ne le rend pas ingéré.

    2. **Le run est-il HONNÊTE ?**  ``vus == ingérés + exclus + échoués``.
       C'est l'équation de complétude. Si elle ne tombe pas juste, des documents ont
       disparu **sans que rien ne les compte** — le pire cas, car il est invisible.

    ``DEGRADED`` = « le run est allé au bout, mais on ne peut pas le déclarer complet ».
    Les deux situations le méritent ; seule la seconde est un bug du pipeline lui-même.

    **Pourquoi ce n'est plus « aucune compensation ».** L'ancienne version ne regardait
    que ``SAGA_COMPENSATION_STARTED`` — elle ratait donc toute fuite survenue AVANT la
    saga. C'est exactement ce qui est arrivé : 98 documents rejetés à l'embedding (chunk
    hors fenêtre du modèle) n'ont jamais atteint la saga, donc jamais compensé, donc le
    run s'est déclaré ``ok`` en ayant perdu 8 % du corpus. **Un critère qui nomme UNE
    cause ne voit pas les autres.** L'équation, elle, ne nomme aucune cause : elle les
    attrape toutes, y compris celles qu'on n'a pas encore rencontrées.

    Le référentiel est ``document.fetched``, jamais ``document.parsed`` : un document
    invalidé n'est *pas* parsé (``parse_documents`` émet ``INVALIDATED`` **à la place**
    de ``PARSED``, puis ``continue``). Prendre ``parsed`` pour total exclurait les
    invalides du dénominateur — l'équation tomberait juste en oubliant précisément ceux
    qu'elle doit compter.
    """
    seen = stats.counts.get(DOCUMENT_FETCHED, 0)
    if not seen:
        # Rien vu, rien à rendre : un run à vide est complet, pas dégradé.
        return RunStatus.OK

    failed = stats.counts.get(DOCUMENT_FAILED, 0)
    accounted = (
        stats.counts.get(DOCUMENT_PERSISTED, 0)
        + stats.counts.get(DOCUMENT_INVALIDATED, 0)
        + failed
    )

    # `!=` et non `<` : un excédent est une anomalie aussi (double comptage) et doit se
    # voir, plutôt que de passer pour un succès.
    if failed or accounted != seen:
        return RunStatus.DEGRADED
    return RunStatus.OK
