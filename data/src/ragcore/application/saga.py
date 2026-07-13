import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ragcore.core.models.audit import build_event
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import (
    SAGA_COMPENSATION_COMPLETED,
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
            failed_name = steps[failed_index].name if failed_index < len(steps) else "unknown"

            self._telemetry.log(
                "warning",
                "saga.compensation.triggered",
                failed_step=failed_name,
            )
            self._telemetry.emit(
                build_event(
                    event_type=SAGA_COMPENSATION_STARTED,
                    run_id=context.run_id,
                    owner_id=context.owner_id,
                    source=context.source,
                    payload={"failed_step": failed_name},
                    success=False,
                    error_message=str(original_exc),
                )
            )

            for step in reversed(completed):
                try:
                    await step.compensate()
                except Exception as comp_exc:
                    logger.error(
                        "compensation.failed step=%s error=%s",
                        step.name,
                        str(comp_exc),
                    )

            self._telemetry.log("info", "saga.compensation.completed")
            self._telemetry.emit(
                build_event(
                    event_type=SAGA_COMPENSATION_COMPLETED,
                    run_id=context.run_id,
                    owner_id=context.owner_id,
                    source=context.source,
                    payload={
                        "failed_step": failed_name,
                        "compensated_steps": [s.name for s in completed],
                    },
                    success=True,
                )
            )

            raise original_exc
