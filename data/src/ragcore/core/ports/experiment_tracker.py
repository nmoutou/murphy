"""``ExperimentTracker`` — le port du §9 : lever l'opacité du hash.

``fingerprint()`` nomme la collection Qdrant par un hash de 32 caractères. C'est
volontairement illisible (cf. ``config/fingerprint.py``) : un nom parlant
redeviendrait le nom fragile que le hash remplace. Mais un hash ne se lit pas — et
sans un endroit qui associe ce hash à la config **en clair**, l'A/B que §6 rend
*possible* resterait illisible en pratique. On saurait que deux collections
existent ; on ne saurait pas *ce qui les distingue*.

Ce port est cet endroit. Un run d'expérience porte :

- un **run-id** = le fingerprint de la ``WorkflowConfig`` — le MÊME hash que la
  collection Qdrant, par construction (le hook passe l'un dérivé de l'autre) ;
- des **paramètres** = la config de workflow, en clair — la normalisation, la
  stratégie de chunking, le modèle d'embedding : très exactement ce que le hash
  compresse ;
- des **métriques** = ce que le run a compté (le ``RunSummary`` : statut, durées,
  compteurs, vocabulaire non reconnu).

**Pourquoi un port, et pas un appel direct à MLflow dans le hook.** MLflow tire une
lourde arborescence (scipy, pandas, un serveur) : l'exiger pour lancer un `kedro
run` violerait la règle du dépôt — l'embedding local est déjà un extra pour la même
raison (torch). Le port permet au ``NoopExperimentTracker`` d'être le défaut : un
run tourne sans serveur MLflow, sans dépendance ajoutée, et le tracking est un
adaptateur qu'on **branche** quand on veut lire l'A/B — jamais une précondition du
pipeline.

**Le cycle de vie épouse celui du pipeline**, sans que le port connaisse Kedro :

    start_run(run_id, params)   ← before_pipeline_run, une fois le fingerprint dérivé
    log_summary(summary)        ← after_pipeline_run / on_pipeline_error
    end_run()                   ← idem, en finally

``log_summary`` prend le ``RunSummary`` entier plutôt qu'une suite de ``log_metric``
épars : les métriques d'un run ragcore ne sont pas produites au fil de l'eau, elles
sont *connues d'un coup* à la fin (l'agrégat réduit). Émietter le bilan en appels
séparés obligerait chaque adaptateur à refaire la même projection ``RunSummary`` →
métriques ; le faire une fois, ici, laisse à l'adaptateur le seul travail qui lui
revient : la traduction vers son backend.
"""

from typing import Protocol, runtime_checkable

from ..config.workflow import WorkflowConfig
from ..models.identifiers import RunId
from ..models.run_summary import RunSummary


@runtime_checkable
class ExperimentTracker(Protocol):
    """Un run d'expérience : son identité (le fingerprint), ses paramètres, son bilan.

    Le typage est **structurel** : ni ``MlflowExperimentTracker`` ni
    ``NoopExperimentTracker`` n'héritent de ce Protocol. ``tests/unit`` EXÉCUTE la
    promesse qu'ils ont la même forme (``isinstance`` contre ce ``runtime_checkable``).
    """

    def start_run(self, run_id: RunId, params: WorkflowConfig) -> None:
        """Ouvre le run et fige ses paramètres.

        ``run_id`` est le fingerprint de ``params`` — le hook les dérive l'un de
        l'autre, jamais deux fois, pour qu'ils ne puissent pas diverger. Rejouer la
        même config rouvre le même run-id : c'est voulu, l'A/B compare des runs de
        même identité.
        """
        ...

    def log_summary(self, summary: RunSummary) -> None:
        """Enregistre le bilan du run : statut, durées, compteurs, non-reconnus.

        Appelé une fois, en fin de run, quand l'agrégat est réduit. L'adaptateur en
        tire ses métriques ; il ne reçoit jamais de mesure au fil de l'eau.
        """
        ...

    def end_run(self) -> None:
        """Ferme le run. Doit être appelé en ``finally`` : un run laissé ouvert
        resterait « en cours » dans le backend, et le suivant s'y grefferait.
        """
        ...
