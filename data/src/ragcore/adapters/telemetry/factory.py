"""La fabrique de piles de télémétrie — une par worker (§11).

C'est le dernier maillon. Avec un pool, il n'y a plus *un* agrégateur mais N : le
hook ne peut plus construire une instance unique et la partager. Il construit une
**fabrique**, et chaque worker appelle ``build()`` pour obtenir sa pile — son
agrégat, son fichier JSONL, ses clients Mongo posés sur SA boucle.

C'est cela qui fait DISPARAÎTRE le verrou au lieu de le déplacer. Garder des
backends partagés aurait fait réapparaître le ``threading.Lock`` ailleurs — dans
le handle de fichier, dans le client Motor — sans rien gagner. Ici, il n'y a plus
d'objet partagé du tout : un worker qui écrit dans SON fichier n'a personne avec
qui se coordonner.

Le ``worker_id`` entre dans le nom du fichier d'événements : c'est ce qui permet à
N workers d'écrire en parallèle sans s'entrelacer, et de relire après coup la trace
de chacun.
"""

from datetime import datetime
from pathlib import Path

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.services.telemetry_registry import TelemetryRegistry
from ragcore.core.telemetry_events import EVENT_CATALOG

from .aggregator import RunStatsAggregator
from .console_log import ConsoleLogTelemetry
from .jsonl_file import JsonlFileTelemetry
from .mongo_audit import MongoAuditTelemetryAdapter
from .noop import NoopTelemetry
from .registry_aware import RegistryAwareTelemetry
from .worker_backends import WorkerBackends

__all__ = ["WorkerTelemetryFactory"]


class WorkerTelemetryFactory:
    """Implémentation de ``TelemetryFactory``.

    ``audit_repo_factory`` prend le runtime du worker et rend un ``AuditRepository``
    posé dessus. C'est une FABRIQUE et non un dépôt : un client Motor partagé serait
    lié à la boucle de son créateur, et le worker ne pourrait pas s'en servir. Passer
    ``None`` désactive l'audit Mongo (mode local / test).
    """

    def __init__(  # noqa: PLR0913 — l'identité du run + ses sorties ; les grouper les cacherait
        self,
        run_id: RunId,
        owner_id: OwnerId,
        source: SourceName | None,
        started_at: datetime,
        events_dir: Path,
        audit_repo_factory: object | None = None,
    ) -> None:
        self._run_id = run_id
        self._owner_id = owner_id
        self._source = source
        self._started_at = started_at
        self._events_dir = Path(events_dir)
        self._audit_repo_factory = audit_repo_factory
        self._registry = TelemetryRegistry.from_catalog(EVENT_CATALOG)

    def build(self, worker_id: int, runtime: AsyncRuntime) -> RegistryAwareTelemetry:
        aggregator = RunStatsAggregator(
            run_id=self._run_id,
            owner_id=self._owner_id,
            source=self._source,
            started_at=self._started_at,
        )

        jsonl = JsonlFileTelemetry(
            events_dir=self._events_dir,
            run_id=f"{self._run_id}-w{worker_id}",
            started_at=self._started_at,
        )

        mongo: TelemetryPort = NoopTelemetry()
        if self._audit_repo_factory is not None:
            audit_repo = self._audit_repo_factory(runtime)  # type: ignore[operator]
            mongo = MongoAuditTelemetryAdapter(audit_repo, runtime)

        return RegistryAwareTelemetry(
            registry=self._registry,
            backends=WorkerBackends(
                log=ConsoleLogTelemetry(),
                jsonl=jsonl,
                mongo=mongo,
                aggregate=aggregator,
            ),
        )
