"""``build_experiment_tracker`` — settings d'infra → le tracker à brancher.

Le hook ne doit pas connaître les deux implémentations ni la règle qui les départage :
il demande « le tracker », et cette fabrique la lui rend. C'est le seul endroit qui
sait que ``tracking_provider=noop`` (le défaut, sans dépendance) donne un
``NoopExperimentTracker``, et que ``mlflow`` suppose l'extra installé.

**L'import de ``mlflow`` reste paresseux même ici.** Construire ``MlflowExperimentTracker``
n'importe pas ``mlflow`` (l'adaptateur le fait à l'usage, dans ``_mlflow()``) : la
fabrique peut donc l'instancier sans payer l'arborescence tant qu'aucun run ne démarre.
"""

from ragcore.adapters.config.settings import InfraSettings
from ragcore.core.ports.experiment_tracker import ExperimentTracker

from .mlflow_tracker import MlflowExperimentTracker
from .noop_tracker import NoopExperimentTracker

__all__ = ["build_experiment_tracker"]


def build_experiment_tracker(settings: InfraSettings) -> ExperimentTracker:
    """Le tracker dicté par l'infra. ``noop`` par défaut, ``mlflow`` sur demande."""
    if settings.tracking_provider == "mlflow":
        return MlflowExperimentTracker(tracking_uri=settings.mlflow_tracking_uri)
    return NoopExperimentTracker()
