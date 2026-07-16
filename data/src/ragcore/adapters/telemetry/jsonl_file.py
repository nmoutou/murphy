"""Journal d'audit local : un événement par ligne, en JSONL.

Le ``threading.Lock`` d'avant a disparu — comme celui de l'agrégateur, il est
devenu *sans objet*. Il protégeait un fichier partagé par tous les threads ; la
fabrique (§11) donne désormais à chaque worker **son** fichier (``run_id-wN``).
Un worker qui écrit dans son propre fichier n'a personne avec qui se coordonner.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ragcore.core.models.audit import AuditEvent
from ragcore.core.services.run_artifacts import run_scoped_filename


class JsonlFileTelemetry:
    """Écrit chaque AuditEvent dans le fichier JSONL d'UN worker.

    Append-only : le fichier est la trace brute du run, relisible après coup sans
    base de données.
    """

    def __init__(self, events_dir: Path, run_id: str, started_at: datetime) -> None:
        self._path = Path(events_dir) / run_scoped_filename(
            run_id, started_at, ".jsonl"
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: AuditEvent) -> None:
        # On NE rattrape PAS l'OSError ici : l'avaler d'un `warning` empêchait le
        # fan-out (`RegistryAwareTelemetry._deliver`) de la compter en
        # `AUDIT_WRITE_FAILED`. Une ligne d'audit perdue doit dégrader le run — et
        # c'est `_deliver` qui isole ET compte. L'invariant « la télémétrie ne fait
        # jamais échouer l'ingestion » tient là-haut, pas ici.
        line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def log(self, level: str, message: str, **context: Any) -> None:
        return
