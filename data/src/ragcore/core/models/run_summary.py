"""RunSummary — la PROJECTION identifiée d'un RunStats.

Deux modèles, deux natures, et la frontière n'est pas cosmétique :

- ``RunStats`` est *calculé*. Il n'a pas d'identité, il fusionne (monoïde), et il
  en existe N par run — un par worker.
- ``RunSummary`` est *déclaré*. Il porte l'identité du run (run_id, dates,
  statut) et il en existe exactement UN. Il ne fusionne pas.

Confondre les deux obligerait à répondre à « quel ``run_id`` gagne quand on fusionne
deux sommaires ? » — question sans réponse commutative, donc source de
non-déterminisme silencieux. On ne la pose jamais : l'identité s'attache APRÈS la
réduction, une seule fois, par ``RunSummary.of()``.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ragcore.core.telemetry_events import (
    AUDIT_WRITE_FAILED,
    DOCUMENT_FAILED,
    DOCUMENT_FETCHED,
    DOCUMENT_INVALIDATED,
    DOCUMENT_PERSISTED,
)

from .enums import SourceName
from .identifiers import RunId
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

    run_id: RunId
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
            source=source,
            status=status,
            started_at=started_at,
            ended_at=ended_at or datetime.now(UTC),
            stats=stats,
            error_message=error_message,
        )


def _status_from(stats: RunStats) -> RunStatus:
    """``OK`` seulement si TOUT ce qui a été vu a été ingéré — ou écarté sciemment.

    Trois propriétés distinctes, qu'il ne faut pas confondre, et qui mènent toutes à
    ``DEGRADED`` :

    1. **Le run a-t-il tout ingéré ?**  ``échoués == 0``.
       Un document qui échoue est un document perdu, *même déclaré*. Le déclarer le rend
       rejouable ; ça ne le rend pas ingéré.

    2. **Le run est-il HONNÊTE ?**  ``vus == ingérés + exclus + échoués``.
       C'est l'équation de complétude. Si elle ne tombe pas juste, des documents ont
       disparu **sans que rien ne les compte** — le pire cas, car il est invisible.

    3. **Le run est-il CROYABLE ?**  ``audit.write.failed == 0``.
       Les deux premières propriétés se lisent dans des compteurs. Si l'audit qui produit
       ces compteurs a perdu des écritures, alors leur verdict ne vaut plus rien : une
       équation qui tombe juste sur des chiffres incomplets ne prouve rien du tout. Un
       audit troué ne dit pas *qu'il manque des documents* — il dit qu'on **ne peut plus
       savoir** s'il en manque, ce qui est précisément le cas qu'on refuse de laisser
       passer pour `ok`.

    ``DEGRADED`` = « le run est allé au bout, mais on ne peut pas le déclarer complet ».
    Les trois situations le méritent ; seules les deux dernières sont un bug du pipeline
    lui-même.

    **Pourquoi ce n'est plus « aucune compensation ».** L'ancienne version ne regardait
    que ``SAGA_COMPENSATION_STARTED`` — elle ratait donc toute fuite survenue AVANT la
    saga. C'est exactement ce qui est arrivé : 98 documents rejetés à l'embedding (chunk
    hors fenêtre du modèle) n'ont jamais atteint la saga, donc jamais compensé, donc le
    run s'est déclaré ``ok`` en ayant perdu 8 % du corpus. **Un critère qui nomme UNE
    cause ne voit pas les autres.** L'équation, elle, ne nomme aucune cause : elle les
    attrape toutes, y compris celles qu'on n'a pas encore rencontrées.

    Le référentiel est ``document.fetched``, jamais ``document.parsed`` : un document
    invalidé n'est *pas* parsé (``compute_idempotence`` émet ``INVALIDATED`` **à la place**
    de ``PARSED``, puis ``continue``). Prendre ``parsed`` pour total exclurait les
    invalides du dénominateur — l'équation tomberait juste en oubliant précisément ceux
    qu'elle doit compter.
    """
    # ⚠️ AVANT le court-circuit « rien vu », et ce n'est pas un détail d'ordre : un audit
    # défaillant peut avoir perdu jusqu'au `document.fetched`. Tester la complétude en
    # premier ferait alors passer un run aveugle pour un run à vide — donc pour un `ok`.
    # La propriété la plus faible (« mes compteurs sont-ils fiables ? ») se vérifie
    # d'abord, parce que toutes les autres en dépendent.
    if stats.counts.get(AUDIT_WRITE_FAILED, 0):
        return RunStatus.DEGRADED

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
