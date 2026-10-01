"""La fabrique de piles de télémétrie — une par worker (§11).

C'est le dernier maillon. Avec un pool, il n'y a plus *un* agrégateur mais N : le
hook ne peut plus construire une instance unique et la partager. Il construit une
**fabrique**, et chaque worker appelle ``build()`` pour obtenir sa pile — son
agrégat, ses clients Mongo posés sur SA boucle.

C'est cela qui fait DISPARAÎTRE le verrou au lieu de le déplacer. Garder des
backends partagés aurait fait réapparaître le ``threading.Lock`` ailleurs — dans
le client Motor — sans rien gagner. Ici, il n'y a plus d'objet partagé du tout.
"""

from datetime import datetime

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.ports.runtime import AsyncRuntime
from ragcore.core.ports.telemetry import TelemetryPort
from ragcore.core.services.telemetry_registry import TelemetryRegistry
from ragcore.core.telemetry_events import EVENT_CATALOG

from .aggregator import RunStatsAggregator
from .console_log import ConsoleLogTelemetry
from .mongo_audit import MongoAuditTelemetryAdapter
from .noop import NoopTelemetry
from .registry_aware import RegistryAwareTelemetry
from .worker_backends import WorkerBackends

__all__ = ["WorkerTelemetryFactory", "assemble_telemetry"]


def assemble_telemetry(
    registry: TelemetryRegistry,
    *,
    mongo: TelemetryPort,
    aggregate: RunStatsAggregator,
) -> RegistryAwareTelemetry:
    """Le CÂBLAGE d'une pile de télémétrie : registry + les trois backends.

    La console est toujours la même ; les deux autres varient (audit Mongo optionnel,
    agrégat propre). Ce montage était recopié à
    l'identique dans deux endroits — la fabrique par worker ci-dessous ET le hook, pour
    sa pile de run-lifecycle. Le grouper ici fait qu'un backend ajouté ou réordonné se
    voit en UN point, pas deux.
    """
    return RegistryAwareTelemetry(
        registry=registry,
        backends=WorkerBackends(
            log=ConsoleLogTelemetry(),
            mongo=mongo,
            aggregate=aggregate,
        ),
    )


class WorkerTelemetryFactory:
    """Implémentation de ``TelemetryFactory``.

    ``audit_repo_factory`` prend le runtime du worker et rend un ``AuditRepository``
    posé dessus. C'est une FABRIQUE et non un dépôt : un client Motor partagé serait
    lié à la boucle de son créateur, et le worker ne pourrait pas s'en servir. Passer
    ``None`` désactive l'audit Mongo (mode local / test).
    """

    def __init__(
        self,
        run_id: RunId,
        source: SourceName | None,
        started_at: datetime,
        audit_repo_factory: object | None = None,
    ) -> None:
        self._run_id = run_id
        self._source = source
        self._started_at = started_at
        self._audit_repo_factory = audit_repo_factory
        self._registry = TelemetryRegistry.from_catalog(EVENT_CATALOG)

    def build(self, worker_id: int, runtime: AsyncRuntime) -> RegistryAwareTelemetry:
        aggregator = RunStatsAggregator(
            run_id=self._run_id,
            source=self._source,
            started_at=self._started_at,
        )

        mongo: TelemetryPort = NoopTelemetry()
        if self._audit_repo_factory is not None:
            audit_repo = self._audit_repo_factory(runtime)  # type: ignore[operator]
            mongo = MongoAuditTelemetryAdapter(audit_repo, runtime)

        return assemble_telemetry(self._registry, mongo=mongo, aggregate=aggregator)
