from __future__ import annotations

import logging
from pathlib import Path

from ragcore.application.pipeline_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.telemetry_events import MAINTENANCE_CLEANUP_EXECUTED
from ragcore.core.ports.telemetry import TelemetryPort

logger = logging.getLogger(__name__)


def cleanup_node(
    cache_paths: list[str],
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
) -> dict:
    """Delete all files under the parameterized cache paths (no hardcoded paths)."""
    total_deleted = 0
    cleaned: list[str] = []

    for path_str in cache_paths:
        path = Path(path_str)
        if not path.exists():
            continue
        count = 0
        for f in sorted(path.rglob("*"), reverse=True):
            try:
                if f.is_file():
                    f.unlink()
                    count += 1
                elif f.is_dir():
                    f.rmdir()  # only succeeds if empty
            except OSError as exc:
                logger.warning("Could not delete %s: %s", f, exc)
        total_deleted += count
        if count:
            cleaned.append(path_str)

    result = {"total_files_deleted": total_deleted, "directories_cleaned": cleaned}
    telemetry.emit(
        build_event(
            event_type=MAINTENANCE_CLEANUP_EXECUTED,
            run_id=pipeline_context.run_id,
            owner_id=pipeline_context.owner_id,
            source=pipeline_context.source,
            payload=result,
        )
    )
    return result
