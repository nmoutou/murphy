"""``MlflowExperimentTracker`` — l'adaptateur qui lève l'opacité du hash (§9).

Il branche le port ``ExperimentTracker`` sur MLflow. C'est lui qui rend l'A/B
LISIBLE : le fingerprint qui nomme la collection Qdrant devient un run MLflow portant
la ``WorkflowConfig`` **en clair** et les compteurs du bilan.

``mlflow`` est un import PARESSEUX, exactement comme ``torch`` dans ``local_embedder``
et pour la même raison : il tire une lourde arborescence (scipy, pandas, un serveur).
Le hisser en tête du module l'imposerait à tout import de ``ragcore.adapters`` — y
compris aux runs en mode ``noop`` qui n'en ont aucun besoin. L'adaptateur n'est
construit QUE lorsqu'on a explicitement demandé le tracking MLflow ; c'est là, et là
seulement, qu'on paie l'import.

**Le fingerprint n'est pas le ``run_id`` interne de MLflow.** MLflow génère son propre
identifiant (un UUID). On mappe donc notre empreinte sur le ``run_name`` ET un tag
``ragcore.fingerprint`` : le nom la rend visible dans l'UI, le tag la rend
*requêtable* (``search_runs`` sur le tag retrouve tous les rejeux d'une même config).
C'est la traduction attendue d'un port vers un backend : le contrat du port
(« run-id = fingerprint ») est honoré dans le vocabulaire de MLflow, pas trahi par
lui.
"""

from typing import TYPE_CHECKING

from ragcore.core.config.workflow import WorkflowConfig
from ragcore.core.models.identifiers import RunId
from ragcore.core.models.run_summary import RunSummary

if TYPE_CHECKING:
    import mlflow

__all__ = ["MlflowExperimentTracker"]

# Le tag qui porte l'empreinte : c'est LUI qu'on requête pour retrouver tous les
# rejeux d'une même config (le run_name MLflow n'est pas indexé pour la recherche).
_FINGERPRINT_TAG = "ragcore.fingerprint"

# L'expérience MLflow qui regroupe tous les runs d'ingestion. Un nom stable : sans
# lui, MLflow retombe sur « Default » et mélange les runs à ceux d'autres projets.
_EXPERIMENT = "ragcore-ingestion"


class MlflowExperimentTracker:
    """Implémentation de ``ExperimentTracker`` sur un serveur MLflow.

    ``tracking_uri`` est passé explicitement : l'adaptateur ne lit pas
    l'environnement (c'est le rôle de ``adapters/config/``). ``None`` laisse MLflow
    utiliser sa configuration ambiante (fichier local ``mlruns/`` par défaut).
    """

    def __init__(self, tracking_uri: str | None = None) -> None:
        self._tracking_uri = tracking_uri
        self._active = False

    def _mlflow(self) -> "mlflow":
        # noqa: PLC0415 — import paresseux DÉLIBÉRÉ : mlflow tire scipy/pandas/un serveur.
        # Le hisser en tête imposerait ce coût à tout import de `adapters`, y compris aux
        # runs `noop` qui n'en ont aucun besoin (cf. le même motif dans local_embedder).
        import mlflow  # noqa: PLC0415

        return mlflow

    def start_run(self, run_id: RunId, params: WorkflowConfig) -> None:
        mlflow = self._mlflow()
        if self._tracking_uri is not None:
            mlflow.set_tracking_uri(self._tracking_uri)
        mlflow.set_experiment(_EXPERIMENT)

        # `run_name` = l'empreinte (visible dans l'UI) ; le tag la rend requêtable.
        mlflow.start_run(run_name=run_id, tags={_FINGERPRINT_TAG: run_id})
        self._active = True

        # Les paramètres EN CLAIR — très exactement ce que le hash compresse. Aplatis
        # par phase pour rester lisibles dans l'UI : `chunking.size`, `embedding.model`…
        mlflow.log_params(_flatten_params(params))

    def log_summary(self, summary: RunSummary) -> None:
        mlflow = self._mlflow()

        # Le statut n'est pas une métrique numérique : c'est un tag. Il porte le verdict
        # du run (`ok` / `degraded` / `failed`), qu'on filtre dans l'UI.
        mlflow.set_tag("ragcore.status", summary.status.value)

        duration_s = (summary.ended_at - summary.started_at).total_seconds()
        mlflow.log_metric("duration_seconds", duration_s)

        # Les compteurs du run SONT les métriques : `document.persisted`,
        # `document.failed`… MLflow n'accepte pas le point comme nom de métrique, d'où
        # la substitution — mais le nom reste lisible (`document_persisted`).
        for event_type, count in summary.stats.counts.items():
            mlflow.log_metric(_metric_name(event_type), count)

        # Le vocabulaire non reconnu se DÉCLARE aussi côté tracking : un run qui n'a pas
        # tout compris doit le dire ici comme il le dit dans le RunSummary. On logue le
        # NOMBRE de non-reconnus (métrique) — le détail vit dans le bilan Mongo/JSONL.
        unknown_total = sum(len(values) for values in summary.stats.unknowns.values())
        mlflow.log_metric("unknowns_total", unknown_total)

    def end_run(self) -> None:
        # Idempotent : `end_run()` sur une absence de run actif est un no-op côté MLflow,
        # mais on garde le drapeau pour ne pas appeler l'import paresseux inutilement.
        if not self._active:
            return
        self._mlflow().end_run()
        self._active = False


def _flatten_params(config: WorkflowConfig) -> dict[str, object]:
    """``WorkflowConfig`` → dict plat ``phase.champ`` → valeur, pour ``log_params``.

    ``model_dump`` rend un dict imbriqué (``{"chunking": {"size": 128, ...}}``) ;
    MLflow veut des paires plates. On préfixe par la phase pour ne pas collisionner
    (``version`` existe sous ``normalization``, un ``size`` pourrait exister ailleurs).
    """
    flat: dict[str, object] = {}
    for phase, fields in config.model_dump(mode="python").items():
        if isinstance(fields, dict):
            for name, value in fields.items():
                flat[f"{phase}.{name}"] = value
        else:
            flat[phase] = fields
    return flat


def _metric_name(event_type: str) -> str:
    """Un type d'événement (``document.persisted``) → un nom de métrique MLflow.

    MLflow interdit le point dans un nom de métrique : on le remplace par ``_``. Le
    résultat reste lisible et sans ambiguïté (les types d'événements ne se distinguent
    pas par un point isolé).
    """
    return event_type.replace(".", "_")
