from typing import Any, Protocol, runtime_checkable

from ..models.audit import AuditEvent
from ..models.collision_tally import CollisionExample
from ..models.run_stats import RunStats
from ..models.unknown_tally import UnknownExample
from .runtime import AsyncRuntime


@runtime_checkable
class TelemetryPort(Protocol):
    """Émission des événements d'audit et des logs.

    Synchrone : les appelants (saga, use cases, nœuds) émettent depuis du code
    async sans `await`. Un backend qui écrirait en base ferait le pont lui-même.
    """

    def emit(self, event: AuditEvent) -> None:
        """Compte l'événement au bilan du run."""
        ...

    def log(self, level: str, message: str, **context: Any) -> None:
        """Log textuel."""
        ...


@runtime_checkable
class WorkerTelemetry(TelemetryPort, Protocol):
    """La pile de télémétrie d'UN worker : ses backends, son agrégat local."""

    def snapshot(self) -> RunStats:
        """L'agrégat local du worker, à fusionner avec celui des autres."""
        ...

    def close(self) -> None:
        """Ferme les backends du worker."""
        ...

    def record_unknown(
        self, category: str, value: str, example: UnknownExample
    ) -> None:
        """Déclare un mot que le run a vu sans savoir le nommer, dans le document
        ``example``. Un appel par document : c'est ce qui en fait un compte de
        documents.

        Le port RATTRAPE ici ses implémentations : les trois l'exposaient déjà, seul
        le contrat l'ignorait. Ce n'est donc pas un élargissement, c'est un aveu de
        retard.

        L'appelant n'est jamais le parser ni l'extracteur — ils ne voient pas la
        télémétrie du worker. Ils REMONTENT leurs inconnus dans leur valeur de retour
        (``ParseResult``, ``ExtractionResult.unknowns``) ; c'est le worker,
        qui tient cette pile, qui les déclare ici. Sans quoi ``RunStats.unknowns``
        resterait le tuyau vide qu'il est : plombé de bout en bout, et sans producteur.
        """
        ...

    def record_collision(self, key: str, example: CollisionExample) -> None:
        """Déclare une clé de métadonnée qui a reçu plusieurs valeurs dans le document
        dont ``example`` donne les fichiers (ADR-049). Un appel par document et clé.

        Comme pour un inconnu, le parser la remonte (``ParseResult.collisions``,
        ``CollisionError``) et le site de parse la déclare ici.
        """
        ...


@runtime_checkable
class TelemetryFactory(Protocol):
    """Fabrique une pile de télémétrie par worker — une FABRIQUE, pas une instance.

    Avec un pool il n'y a plus *un* agrégateur mais N : le hook ne peut plus
    construire une instance unique. Chaque worker appelle ``build()`` et obtient sa
    pile — sa boucle, ses clients, ses backends.

    C'est ce qui fait DISPARAÎTRE le verrou au lieu de le déplacer : garder les
    backends partagés aurait fait réapparaître le ``threading.Lock`` ailleurs, sans
    rien gagner.
    """

    def build(self, worker_id: int, runtime: AsyncRuntime) -> WorkerTelemetry: ...
