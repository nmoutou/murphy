"""``NoopExperimentTracker`` — le tracker par défaut : il ne trace rien, et c'est voulu.

Le §9 exige un tracker ; il n'exige pas que MLflow tourne pour lancer un `kedro
run`. MLflow tire une lourde arborescence (scipy, pandas, un serveur) — l'imposer au
chemin critique violerait la règle du dépôt (l'embedding local est déjà un extra
pour la même raison). Ce Noop est donc le défaut : un run tourne sans serveur MLflow,
sans dépendance ajoutée, et le tracking devient un adaptateur qu'on **branche** quand
on veut lire l'A/B.

Ce n'est pas un bouchon de test — c'est le comportement de production quand l'extra
``tracking`` n'est pas installé. Il satisfait le port en entier (les trois méthodes
existent et acceptent les bons types) : le pipeline appelle ``start_run`` /
``log_summary`` / ``end_run`` sans savoir — ni avoir à savoir — qu'aucun backend
n'écoute derrière.
"""

from ragcore.core.config.workflow import WorkflowConfig
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_summary import RunSummary

__all__ = ["NoopExperimentTracker"]


class NoopExperimentTracker:
    """Implémentation de ``ExperimentTracker`` qui n'écrit nulle part."""

    def start_run(self, run_id: RunId, params: WorkflowConfig) -> None:
        return None

    def log_summary(self, summary: RunSummary) -> None:
        return None

    def end_run(self) -> None:
        return None
