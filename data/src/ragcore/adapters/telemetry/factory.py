"""La fabrique de piles de télémétrie — une par worker (§11).

C'est le dernier maillon. Avec un pool, il n'y a plus *un* agrégateur mais N : le
hook ne peut plus construire une instance unique et la partager. Il construit une
**fabrique**, et chaque worker appelle ``build()`` pour obtenir sa pile — son agrégat
à lui.

C'est cela qui fait DISPARAÎTRE le verrou au lieu de le déplacer : il n'y a plus
d'objet partagé du tout.
"""

from datetime import datetime

from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import RunId
from ragcore.core.ports.runtime import AsyncRuntime

from .aggregator import RunStatsAggregator
from .console_log import ConsoleLogTelemetry
from .worker_backends import WorkerBackends
from .worker_stack import WorkerTelemetryStack

__all__ = ["WorkerTelemetryFactory", "assemble_telemetry"]


def assemble_telemetry(aggregate: RunStatsAggregator) -> WorkerTelemetryStack:
    """Le CÂBLAGE d'une pile de télémétrie : ses backends.

    La console est toujours la même ; l'agrégat est propre à chaque pile. Ce montage
    sert deux endroits — la fabrique par worker ci-dessous ET le hook, pour sa pile de
    run-lifecycle. Le grouper ici fait qu'un backend ajouté ou réordonné se voit en UN
    point, pas deux.
    """
    return WorkerTelemetryStack(
        WorkerBackends(log=ConsoleLogTelemetry(), aggregate=aggregate)
    )


class WorkerTelemetryFactory:
    """Implémentation de ``TelemetryFactory`` : une pile neuve par worker."""

    def __init__(
        self,
        run_id: RunId,
        sources: tuple[SourceName, ...],
        started_at: datetime,
    ) -> None:
        self._run_id = run_id
        self._sources = sources
        self._started_at = started_at

    def build(self, worker_id: int, runtime: AsyncRuntime) -> WorkerTelemetryStack:
        del (
            worker_id,
            runtime,
        )  # la pile vit en mémoire : ni boucle ni identité requises
        aggregator = RunStatsAggregator(
            run_id=self._run_id,
            sources=self._sources,
            started_at=self._started_at,
        )
        return assemble_telemetry(aggregator)
