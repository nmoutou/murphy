from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ragcore.application.run_context import PipelineContext
from ragcore.core.models.audit import build_event
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.telemetry_events import MAINTENANCE_CLEANUP_EXECUTED

logger = logging.getLogger(__name__)


def cleanup_node(
    cache_paths: list[str],
    pipeline_context: PipelineContext,
    telemetry: TelemetryPort,
) -> dict[str, Any]:
    """Delete all files under the parameterized cache paths (no hardcoded paths)."""
    total_deleted = 0
    cleaned: list[str] = []
    for path_str in cache_paths:
        count = _clear(Path(path_str))
        total_deleted += count
        if count:
            cleaned.append(path_str)

    result = {"total_files_deleted": total_deleted, "directories_cleaned": cleaned}
    telemetry.emit(
        build_event(
            event_type=MAINTENANCE_CLEANUP_EXECUTED,
            run_id=pipeline_context.run_id,
            source=pipeline_context.source,
            payload=result,
        )
    )
    return result


def _clear(path: Path) -> int:
    """Vide ``path`` (fichiers, puis dossiers devenus vides). Rend le nombre de
    fichiers supprimés ; un chemin absent n'a rien à vider."""
    if not path.exists():
        return 0
    count = 0
    for entry in sorted(path.rglob("*"), reverse=True):
        try:
            if entry.is_file():
                entry.unlink()
                count += 1
            elif entry.is_dir():
                entry.rmdir()  # only succeeds if empty
        except OSError as exc:
            logger.warning("Could not delete %s: %s", entry, exc)
    return count
