from typing import Any, Protocol, runtime_checkable

from ..models.audit import AuditEvent
from ..models.run_stats import RunStats
from ..models.unknown_tally import UnknownExample
from .runtime import AsyncRuntime


@runtime_checkable
class TelemetryPort(Protocol):
    """Synchrone : les appelants émettent depuis du code async sans `await`. Un backend
    qui écrirait en base ferait le pont lui-même.
    """

    def emit(self, event: AuditEvent) -> None:
        """Compte l'événement au bilan du run."""
        ...

    def log(self, level: str, message: str, **context: Any) -> None: ...


@runtime_checkable
class WorkerTelemetry(TelemetryPort, Protocol):
    """La pile de télémétrie d'un worker : ses backends, son agrégat local."""

    def snapshot(self) -> RunStats:
        """À fusionner avec celui des autres workers."""
        ...

    def close(self) -> None: ...

    def record_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> None:
        """Un mot que le run a vu sans savoir le nommer, dans le document ``example``.
        Un appel par document : c'est un compte de documents.

        Appelé par le worker, jamais par le parser ni l'extracteur : ils remontent leurs
        inconnus dans leur valeur de retour.
        """
        ...

    def record_collision(self, key: str, source_files: tuple[str, ...]) -> None:
        """Une clé de métadonnée qui a reçu plusieurs valeurs dans le document de
        fichiers ``source_files`` (ADR-049). Un appel par document et par clé.
        """
        ...


@runtime_checkable
class TelemetryFactory(Protocol):
    """Une pile de télémétrie par worker, avec ses backends : rien de partagé, donc
    aucun verrou.
    """

    def build(self, worker_id: int, runtime: AsyncRuntime) -> WorkerTelemetry: ...
