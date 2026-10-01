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
        """Du dernier au premier. Rend les compensations ratées."""
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
            # Écrit partiel laissé derrière : émis et compté, pour qu'il se voie au bilan
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
                # Une seule compensation ratée suffit : le rollback n'est pas propre
                success=not failed_compensations,
            )
        )
