from typing import Any, Protocol, runtime_checkable

from ..models.audit import AuditEvent
from ..models.collision_record import CollisionRecord
from ..models.problems import FileProblem
from ..models.run_measures import MeasurePath, RunMeasures
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

    def record_measure(self, path: MeasurePath, value: float, ref: str) -> None:
        """Une taille ou une durée pour ``statistics`` (ADR-034 §8), jamais pour le
        bilan. ``ref`` nomme ce qui est mesuré, un document le plus souvent."""
        ...

    def snapshot_measures(self) -> RunMeasures:
        """À fusionner avec celles des autres workers."""
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

    def record_collision(self, record: CollisionRecord) -> None:
        """Une collision, comptée au bilan et détaillée dans
        ``MURPHY_PROBLEMS.collisions``.
        Un appel par document et par clé.

        Seule la pile du hook garde le détail : lecture et parse tournent dans le
        thread du nœud, jamais dans un worker, dont le détail serait perdu.
        """
        ...

    def record_problem(self, problem: FileProblem) -> None:
        """Le détail d'un fichier écarté par le connecteur, pour ``MURPHY_PROBLEMS``.
        Son compte arrive par l'événement de sa raison, jamais par ici."""
        ...

    def record_invalidation(self, reason: str) -> None:
        """Un document rejeté au parse, sous sa raison (``exclusion_reasons``). Un appel
        par ``document.invalidated`` émis."""
        ...


@runtime_checkable
class TelemetryFactory(Protocol):
    """Une pile de télémétrie par worker, avec ses backends : rien de partagé, donc
    aucun verrou.
    """

    def build(self, worker_id: int, runtime: AsyncRuntime) -> WorkerTelemetry: ...
