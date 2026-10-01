"""La télémétrie qui S'OBSERVE ELLE-MÊME.

Le système comptait ce qu'il *émettait* ; il ne vérifiait pas que ce qu'il avait émis
était *arrivé*. Quatre points avalaient une écriture d'audit ratée — tous la logguaient
en ``warning``, aucun ne la comptait :

1. ``AsyncioRuntime._drain``      — ``gather(return_exceptions=True)``, résultat JETÉ
2. ``MongoAuditTelemetryAdapter`` — ``except`` → ``warning`` (branche sync)
3. ``RegistryAwareTelemetry.emit``  — un ``except`` par backend
4. ``RegistryAwareTelemetry.close`` — idem à la fermeture

Le principe « la télémétrie ne fait jamais échouer l'ingestion » n'est pas remis en
cause : ces exceptions restent isolées. Ce qui change, c'est que *ne pas casser* ne
signifie plus *ne pas dire*. Chacune de ces pertes émarge désormais à
``audit.write.failed``, donc au bilan, donc au statut du run.

Ces tests provoquent l'échec — c'est leur seule raison d'être. Aucun test existant ne
savait le faire : ils vérifiaient tous le chemin nominal, où rien ne rate.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from ragcore.adapters.runtime.asyncio_runtime import AsyncioRuntime
from ragcore.adapters.telemetry.aggregator import RunStatsAggregator
from ragcore.adapters.telemetry.registry_aware import RegistryAwareTelemetry
from ragcore.adapters.telemetry.worker_backends import WorkerBackends
from ragcore.core.models.audit import AuditEvent, build_event
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_stats import RunStats
from ragcore.core.models.run_summary import RunStatus, RunSummary
from ragcore.core.services.telemetry_registry import EventBehavior, TelemetryRegistry
from ragcore.core.telemetry_events import (
    AUDIT_WRITE_FAILED,
    DOCUMENT_FETCHED,
    DOCUMENT_PERSISTED,
)


class ExplodingBackend:
    """Un backend qui refuse d'écrire — le cas qu'aucun test ne savait produire.

    En vrai, c'est un Mongo qui rejette une ligne. En test, c'est ceci : sans lui, le
    chemin d'échec n'est jamais exercé, et un ``except`` qui avale reste vert à jamais.
    """

    def __init__(self, *, on_emit: bool = True, on_close: bool = False) -> None:
        self._on_emit = on_emit
        self._on_close = on_close

    def emit(self, event: AuditEvent) -> None:
        if self._on_emit:
            raise RuntimeError("mongo refuse la ligne")

    def log(self, level: str, message: str, **context: Any) -> None:
        return

    def close(self) -> None:
        if self._on_close:
            raise RuntimeError("le buffer ne se vide pas")


class SilentBackend:
    def emit(self, event: AuditEvent) -> None:
        return

    def log(self, level: str, message: str, **context: Any) -> None:
        return


def _event(event_type: str = DOCUMENT_PERSISTED) -> AuditEvent:
    return build_event(
        event_type=event_type,
        run_id=RunId("r-1"),
    )


async def _boom() -> None:
    """L'écriture d'audit qui rate — un Mongo qui refuse la ligne."""
    raise RuntimeError("mongo refuse la ligne")


async def _fine() -> None:
    """Celle qui passe."""
    return None


async def _settle() -> None:
    """Rend la main à la boucle, le temps que les tâches lancées s'exécutent."""
    await asyncio.sleep(0)


def _telemetry(
    mongo: object, *, aggregator: RunStatsAggregator | None = None
) -> RegistryAwareTelemetry:
    """Une pile réduite à ce qui compte : le backend qui rate, et l'agrégat qui compte."""
    registry = TelemetryRegistry.from_catalog(
        {
            DOCUMENT_PERSISTED: EventBehavior(
                level="info",
                log=False,
                track_mongo=True,
                aggregate=True,
            ),
        }
    )
    return RegistryAwareTelemetry(
        registry=registry,
        backends=WorkerBackends(
            log=SilentBackend(),
            mongo=mongo,  # type: ignore[arg-type]
            aggregate=aggregator
            or RunStatsAggregator(
                run_id=RunId("r-1"),
                source=SourceName.LEGI,
                started_at=datetime.now(UTC),
            ),
        ),
    )


class TestTheFanOutCountsWhatItSwallows:
    """Trou n°3 : ``RegistryAwareTelemetry.emit``."""

    def test_a_backend_that_raises_is_counted(self) -> None:
        telemetry = _telemetry(ExplodingBackend())

        telemetry.emit(_event())

        stats = telemetry.snapshot()
        assert stats.counts[AUDIT_WRITE_FAILED] == 1

    def test_the_ingestion_still_does_not_fail(self) -> None:
        """Le principe tient : compter la perte ne la transforme pas en exception."""
        telemetry = _telemetry(ExplodingBackend())
        telemetry.emit(_event())  # ne lève pas — c'est l'assertion

    def test_the_other_backends_still_receive_the_event(self) -> None:
        """Un backend qui tombe n'emporte pas les autres — ni l'agrégat.

        C'est ce qui rend le compteur lisible : ``document.persisted`` DOIT rester à 1.
        Un run où l'audit Mongo est mort mais où l'agrégat compte encore est
        précisément le cas que `degraded` doit décrire — pas un run vide.
        """
        telemetry = _telemetry(ExplodingBackend())

        telemetry.emit(_event())

        stats = telemetry.snapshot()
        assert stats.counts[DOCUMENT_PERSISTED] == 1

    def test_the_failure_is_not_re_emitted_as_an_event(self) -> None:
        """La récursion est coupée : l'échec va DROIT à l'agrégat.

        Le réémettre par ``emit`` le renverrait vers le backend qui vient de rater —
        qui raterait encore, donc réémettrait. ``audit.write.failed`` porte
        `track_mongo=False` pour la même raison : on n'écrit pas en Mongo qu'on n'a pas
        su écrire en Mongo.
        """
        exploding = CountingExplodingBackend()
        telemetry = _telemetry(exploding)

        telemetry.emit(_event())

        # Une seule tentative d'écriture : celle qui a raté. Pas de seconde vague.
        assert exploding.attempts == 1


class CountingExplodingBackend(ExplodingBackend):
    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    def emit(self, event: AuditEvent) -> None:
        self.attempts += 1
        raise RuntimeError("mongo refuse la ligne")


class TestTheCloseCountsWhatItSwallows:
    """Trou n°4 : ``RegistryAwareTelemetry.close``."""

    def test_a_backend_that_fails_to_close_is_counted(self) -> None:
        """Une fermeture ratée est une PERTE : c'est là qu'un buffer part à la poubelle."""
        telemetry = _telemetry(ExplodingBackend(on_emit=False, on_close=True))

        telemetry.close()

        stats = telemetry.snapshot()
        assert stats.counts[AUDIT_WRITE_FAILED] == 1

    def test_the_aggregate_is_closed_last(self) -> None:
        """Sinon il ne serait plus là pour compter la mort des autres.

        L'agrégat est trié en dernier explicitement, et non par chance du dict : c'est
        un invariant de correction, pas un détail d'ordre d'insertion.
        """
        telemetry = _telemetry(ExplodingBackend(on_emit=False, on_close=True))

        telemetry.close()

        # L'agrégat a survécu assez longtemps pour enregistrer l'échec de `mongo`.
        assert telemetry.snapshot().counts[AUDIT_WRITE_FAILED] == 1


class TestTheDrainSeesWhatItAwaits:
    """Trou n°1 — le plus silencieux, et celui qui porte le gros du volume."""

    def test_a_task_that_raises_is_reported(self) -> None:
        """``return_exceptions=True`` ne supprime pas l'exception : il la RANGE.

        Ce code la rangeait, puis jetait la liste. Une écriture d'audit ratée en
        contexte async ne produisait donc rien — pas même un log.
        """
        runtime = AsyncioRuntime()
        try:
            runtime.spawn(_boom())
            report = runtime.drain()
        finally:
            runtime.close()

        assert report.drained == 1
        assert report.failed == 1

    def test_a_task_that_ALREADY_failed_is_still_reported(self) -> None:
        """Le cas qui a échappé au premier correctif — et c'est le cas COURANT.

        Une écriture d'audit qui rate vite (Mongo refuse la ligne) est **terminée**
        avant que le drain regarde. Or ``asyncio.all_tasks()`` ne rend que les tâches
        *non terminées* : elle avait donc déjà disparu du registre de la boucle, et
        aucun filtre n'aurait pu la rattraper. Son exception partait dans le néant, avec
        pour seule trace le « Task exception was never retrieved » d'asyncio.

        D'où ``spawn`` : le runtime RETIENT ses tâches, et draine sa propre liste.
        """
        runtime = AsyncioRuntime()
        try:
            runtime.spawn(_boom())
            # On force la tâche à s'exécuter (et à échouer) AVANT le drain.
            runtime.run(_settle())
            report = runtime.drain()
        finally:
            runtime.close()

        assert report.failed == 1

    def test_a_clean_run_reports_nothing(self) -> None:
        """Le cas nominal ne paie rien et n'invente rien."""
        runtime = AsyncioRuntime()
        try:
            runtime.spawn(_fine())
            report = runtime.drain()
        finally:
            runtime.close()

        assert report.drained == 1
        assert report.failed == 0

    def test_drain_is_idempotent(self) -> None:
        """Un second drain ne RECOMPTE pas les mêmes échecs.

        Sinon le compteur doublerait à chaque appel et dégraderait le run sur du vent —
        et ``close()`` draine encore de lui-même, donc l'appel double est le cas normal.
        """
        runtime = AsyncioRuntime()
        try:
            runtime.spawn(_boom())

            first = runtime.drain()
            second = runtime.drain()
        finally:
            runtime.close()

        assert first.failed == 1
        assert second.failed == 0

    def test_close_still_drains_on_its_own(self) -> None:
        """``close()`` reste sûr par défaut : qui ne draine pas ne perd pas ses écritures.

        Il perd le *compte*, pas les écritures — d'où ``drain()`` pour qui veut le voir.
        """
        runtime = AsyncioRuntime()
        runtime.spawn(_fine())

        runtime.close()  # ne lève pas, et a bien attendu la tâche

        assert runtime.drain().drained == 0  # boucle fermée : plus rien en vol


class TestTheStatusRefusesToTrustAPatchyAudit:
    """Le point d'arrivée : un audit troué DÉGRADE le run."""

    def _summary(self, stats: RunStats) -> RunSummary:
        return RunSummary.of(
            stats,
            context_run_id=RunId("r-1"),
            source=SourceName.LEGI,
            started_at=datetime.now(UTC),
            status=RunStatus.OK,  # l'appelant CROIT que tout va bien
        )

    def test_a_complete_run_with_a_leaking_audit_is_degraded(self) -> None:
        """L'équation de complétude tombe juste — et ça ne suffit PAS.

        1121 vus, 1121 persistés : le corpus a l'air complet. Mais si l'audit a perdu
        des écritures, ces chiffres eux-mêmes sont suspects. Une équation qui tombe
        juste sur des compteurs incomplets ne prouve rien.
        """
        stats = RunStats(
            counts={
                DOCUMENT_FETCHED: 1121,
                DOCUMENT_PERSISTED: 1121,
                AUDIT_WRITE_FAILED: 1,
            }
        )

        assert self._summary(stats).status is RunStatus.DEGRADED

    def test_an_audit_failure_beats_the_empty_run_shortcut(self) -> None:
        """Le PIÈGE d'ordre : un audit mort peut avoir emporté jusqu'à `document.fetched`.

        Tester la complétude d'abord verrait « rien vu » et conclurait « run à vide,
        donc ok ». Un run aveugle passerait pour un run complet. La propriété la plus
        faible — « mes compteurs sont-ils fiables ? » — se vérifie EN PREMIER.
        """
        stats = RunStats(counts={AUDIT_WRITE_FAILED: 3})

        assert self._summary(stats).status is RunStatus.DEGRADED

    def test_a_clean_run_stays_ok(self) -> None:
        """Le cliquet ne se déclenche pas tout seul : sans échec, rien ne change."""
        stats = RunStats(counts={DOCUMENT_FETCHED: 10, DOCUMENT_PERSISTED: 10})

        assert self._summary(stats).status is RunStatus.OK


class TestTheCountTravelsAcrossWorkers:
    """Le compteur doit atteindre le BILAN, pas mourir dans son worker."""

    def test_audit_failures_merge_like_everything_else(self) -> None:
        """Par le monoïde ``RunStats`` — donc la fusion est déjà correcte et commutative.

        C'est tout l'intérêt d'en faire un event agrégé plutôt qu'un compteur ad hoc :
        il n'y a aucune logique de fusion à écrire, donc aucune à se tromper.
        """
        first = RunStats(counts={AUDIT_WRITE_FAILED: 2})
        second = RunStats(counts={AUDIT_WRITE_FAILED: 1})

        merged = RunStats.reduce([first, second])

        assert merged.counts[AUDIT_WRITE_FAILED] == 3
