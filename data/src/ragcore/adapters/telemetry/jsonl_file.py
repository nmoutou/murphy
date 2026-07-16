"""Journal d'audit local : un événement par ligne, en JSONL.

Le ``threading.Lock`` d'avant a disparu — comme celui de l'agrégateur, il est
devenu *sans objet*. Il protégeait un fichier partagé par tous les threads ; la
fabrique (§11) donne désormais à chaque worker **son** fichier (``run_id-wN``).
Un worker qui écrit dans son propre fichier n'a personne avec qui se coordonner.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ragcore.core.models.audit import AuditEvent

_LOGGER = logging.getLogger(__name__)


class JsonlFileTelemetry:
    """Écrit chaque AuditEvent dans le fichier JSONL d'UN worker.

    Append-only : le fichier est la trace brute du run, relisible après coup sans
    base de données.
    """

    def __init__(self, events_dir: Path, run_id: str, started_at: datetime) -> None:
        self._path = Path(events_dir) / _events_filename(run_id, started_at)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: AuditEvent) -> None:
        line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        try:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as exc:
            # La télémétrie ne fait jamais échouer l'ingestion qu'elle observe.
            _LOGGER.warning("jsonl telemetry: écriture impossible (%s)", exc)

    def log(self, level: str, message: str, **context: Any) -> None:
        return


def _events_filename(run_id: str, started_at: datetime) -> str:
    iso = (
        started_at.strftime("%Y-%m-%dT%H.%M.%S.")
        + f"{started_at.microsecond // 1000:03d}Z"
    )
    return f"{iso}_{run_id}.jsonl"
