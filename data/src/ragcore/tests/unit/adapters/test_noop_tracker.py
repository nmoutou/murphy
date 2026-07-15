"""``NoopExperimentTracker`` — le défaut du §9 : il ne trace rien, et n'exige rien.

Ce n'est pas un bouchon de test mais le comportement de production quand l'extra
``tracking`` n'est pas installé. Le seul contrat à vérifier : les trois méthodes
existent, acceptent les bons types, et ne lèvent jamais — un run doit pouvoir les
appeler sans savoir qu'aucun backend n'écoute.

Aucun ``mlflow`` n'est importé, ni ne doit l'être : c'est tout le point du défaut.
"""

from datetime import UTC, datetime

from ragcore.adapters.tracking import NoopExperimentTracker
from ragcore.core.config.workflow import (
    ChunkingConfig,
    EmbeddingConfig,
    NormalizationConfig,
    WorkflowConfig,
)
from ragcore.core.models.enums import SourceName
from ragcore.core.models.identifiers import OwnerId, RunId
from ragcore.core.models.run_summary import RunStatus, RunSummary


def test_noop_lifecycle_is_inert() -> None:
    tracker = NoopExperimentTracker()
    workflow = WorkflowConfig(
        normalization=NormalizationConfig(version="none"),
        chunking=ChunkingConfig(strategy="s", size=128, overlap=25),
        embedding=EmbeddingConfig(model_name="m", dimension=768),
    )
    started = datetime.now(UTC)
    summary = RunSummary(
        run_id=RunId("abc"),
        owner_id=OwnerId("o"),
        source=SourceName.LEGI,
        status=RunStatus.OK,
        started_at=started,
        ended_at=started,
    )

    # Aucune de ces trois lignes ne doit lever — c'est tout ce qu'un run attend du Noop.
    tracker.start_run(RunId("abc"), workflow)
    tracker.log_summary(summary)
    tracker.end_run()
