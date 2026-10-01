import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ragcore.core.models.audit import build_event
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import (
    SAGA_COMPENSATION_COMPLETED,
    SAGA_COMPENSATION_FAILED,
    SAGA_COMPENSATION_STARTED,
)

from .run_context import PipelineContext

logger = logging.getLogger(__name__)


@dataclass
class SagaStep:
    name: str
    forward: Callable[[], Awaitable[Any]]
    compensate: Callable[[], Awaitable[None]]


class SagaExecutor:
    def __init__(self, telemetry: TelemetryPort) -> None:
        self._telemetry = telemetry

    async def execute(self, steps: list[SagaStep], context: PipelineContext) -> None:
        completed: list[SagaStep] = []

        try:
            for step in steps:
                await step.forward()
                completed.append(step)
        except Exception as original_exc:
            failed_index = len(completed)
            failed_name = (
                steps[failed_index].name if failed_index < len(steps) else "unknown"
            )
            self._announce(context, failed_name, original_exc)
            failures = await self._compensate_all(completed, context, failed_name)
            self._report(context, failed_name, completed, failures)
            raise

    def _announce(
        self, context: PipelineContext, failed_name: str, exc: Exception
    ) -> None:
        self._telemetry.log(
            "warning",
            "saga.compensation.triggered",
            failed_step=failed_name,
        )
        self._telemetry.emit(
            build_event(
                event_type=SAGA_COMPENSATION_STARTED,
                run_id=context.run_id,
                source=context.source,
                payload={"failed_step": failed_name},
                success=False,
                error_message=str(exc),
            )
        )

    async def _compensate_all(
        self, completed: list[SagaStep], context: PipelineContext, failed_name: str
    ) -> list[str]:
        """Compense les steps réussis, du dernier au premier. Rend ceux qui ont raté."""
        failed_compensations: list[str] = []
        for step in reversed(completed):
            if not await self._compensate_one(step, context, failed_name):
                failed_compensations.append(step.name)
        return failed_compensations

    async def _compensate_one(
        self, step: SagaStep, context: PipelineContext, failed_name: str
    ) -> bool:
        try:
            await step.compensate()
        except Exception as comp_exc:  # noqa: BLE001 — une compensation ratée ne doit pas interrompre les suivantes ; l'échec est émis et compté
            # Une compensation qui rate laisse un écrit partiel derrière elle.
            # Le `logger.error` seul le rendait invisible au bilan : on émet
            # donc un événement COMPTÉ (le `step` en cause dans son payload), pour que
            # l'état corrompu apparaisse dans le RunSummary — pas de perte sans compteur.
            logger.error(
                "compensation.failed step=%s error=%s",
                step.name,
                str(comp_exc),
            )
            self._telemetry.emit(
                build_event(
                    event_type=SAGA_COMPENSATION_FAILED,
                    run_id=context.run_id,
                    source=context.source,
                    payload={"step": step.name, "failed_step": failed_name},
                    success=False,
                    error_message=str(comp_exc),
                )
            )
            return False
        return True

    def _report(
        self,
        context: PipelineContext,
        failed_name: str,
        completed: list[SagaStep],
        failed_compensations: list[str],
    ) -> None:
        self._telemetry.log("info", "saga.compensation.completed")
        self._telemetry.emit(
            build_event(
                event_type=SAGA_COMPENSATION_COMPLETED,
                run_id=context.run_id,
                source=context.source,
                payload={
                    "failed_step": failed_name,
                    "compensated_steps": [s.name for s in completed],
                    "failed_compensations": failed_compensations,
                },
                # `success` dit la VÉRITÉ : une seule compensation ratée et le
                # rollback n'est pas propre. L'affirmer `True` inconditionnellement
                # faisait mentir l'audit sur l'intégrité de l'état.
                success=not failed_compensations,
            )
        )
